import requests
import ipaddress
import logging
import json
from apps.greencheck.models import GreencheckIp
from apps.accounts.models import Hostingprovider
import pathlib

from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)


class MicrosoftCloudProvider:
    def retrieve_dataset(self):
        try:
            return requests.get(settings.AZURE_IP_RANGE_JSON_FILE).json()
        except requests.RequestException:
            logger.warning("Unable to fetch file and parse json. Aborting early.")
            return
        except Exception:
            logger.exception("Something really unexpected happened. Aborting")



    def extract_ip_ranges(self, raw_dataset):
        """
        Extract the ip ranges from the raw dataset.
        Return: list of altered IPv4 and IPv6 ranges
        """
        ranges_IPv4, ranges_IPv6 = [], []
        ranges_IPv4 = self.convert_to_networks(raw_dataset, ipaddress.IPv4Network)
        ranges_IPv6 = self.convert_to_networks(raw_dataset, ipaddress.IPv6Network)

        try:
            logger.info(f"Looking IPs for Microsoft (Azure)")

            # Retrieve hosting provider by ID from the database
            hoster = Hostingprovider.objects.get(pk = settings.AZURE_PROVIDER_ID) 
        except Hostingprovider.DoesNotExist as e:
            logger.warning(f"Hoster Microsoft (Azure) not found")
            raise e
            
        # Check if lists are not empty
        assert len(ranges_IPv4) > 0
        assert len(ranges_IPv6) > 0

        return { 
            "ipv4": self.update_ranges_in_db(hoster, ranges_IPv4), 
            "ipv6": self.update_ranges_in_db(hoster, ranges_IPv6)
            }

    def convert_to_networks(self, ips_with_mask, ip_version = None):
        """
        Convert ip addresses and subnets of the providers into networks (lib: ipaddress).
        Return: List of networks extracted from the given dataset as parameter.
        """
        list_of_networks = set()

        # Considering the specific JSON structure of this provider, extract the ip addresses and subnet masks
        for services in ips_with_mask['values']:
            for ip_with_mask in services['properties']['addressPrefixes']:
                # Generate network (lib: ipaddress) based on ip and subnet mask
                network = ipaddress.ip_network(ip_with_mask) 
                
                if ip_version == None:
                    # If no version is specified: include all
                    list_of_networks.add(network) 
                elif type(network) == ip_version:
                    # Otherwise: include only the specified ip version (IPv4 or IPv6)
                    list_of_networks.add(network)

        return list(list_of_networks)

    def update_ranges_in_db(self, hoster, ip_networks):
        """
        Go over the list of ips in the network and request updating a record or creating a 
        new one if it does not already exist.
        Return: list of altered ip ranges, whereas each list item represents a record in the database.
        """
        altered_ranges = []
        logger.debug(hoster)
        logger.debug(f"ip_networks length: {len(ip_networks)}")

        for ip_network in ip_networks:
            db_record = self.update_range_in_db(hoster, ip_network[0], ip_network[-1])
            if db_record:
                altered_ranges.append(db_record)

        return altered_ranges

    def update_range_in_db(
        self,
        hoster: Hostingprovider,
        first: ipaddress.IPv4Address,
        last: ipaddress.IPv4Address,
    ):
        """
        Update a single record representing a range associated with a provider/hoster
        Return: (if a new object was created) object (gcip) which is created or updated
        """
        # TODO: decide if we need to optimise this: it might take a long time to update 
        # the database with a big dataset. 
        # Especially if we plan on including more providers 
        
        # Update a specific range of a provider/hoster.
        # (by using first and last, we specify the range)
        gcip, created = GreencheckIp.objects.update_or_create(
            active = True, 
            ip_start = first, 
            ip_end = last, 
            hostingprovider = hoster
        )
        gcip.save() # Save the newly created or updated object

        if created:
            # Only log and return when a new object was created
            logger.debug(gcip)
            return gcip


class Command(BaseCommand):
    help = "Update IP ranges for cloud providers that publish them"

    def handle(self, *args, **options):        
        azure = MicrosoftCloudProvider()
        
        # Retrieve dataset and parse to networks
        dataset = azure.retrieve_dataset()
        ip_ranges = azure.extract_ip_ranges(dataset)

        green_ipv4s = [x for x in ip_ranges if isinstance(x, ipaddress.IPv4Network)]
        green_ipv6s = [x for x in ip_ranges if isinstance(x, ipaddress.IPv6Network)]
        self.stdout.write(
            f"Import Complete: Added {len(green_ipv4s)} new IPV4 networks, "
            f"and {len(green_ipv6s) } IPV6 networks"
        )

