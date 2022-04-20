import requests
import ipaddress
import logging
import json
from apps.greencheck.models import GreencheckIp
from apps.accounts.models import Hostingprovider

from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)

GREEN_REGIONS = (
    ("Azure", "azure-code", settings.AZURE_PROVIDER_ID),
)

class MicrosoftCloudProvider:
    def retrieve(self):
        with open('apps/greencheck/management/commands/azure-ip-ranges.json') as json_file:
            return json.load(json_file)

    def process(self, raw_dataset):
        green_ipv4_ranges = green_ipv6_ranges = []
        green_ipv4_ranges = self.convert_to_networks(raw_dataset, ipaddress.IPv4Network)
        green_ipv6_ranges = self.convert_to_networks(raw_dataset, ipaddress.IPv6Network)

        try:
            logger.info(f"Looking IPs for Azure")
            hoster = Hostingprovider.objects.get(pk = settings.AZURE_PROVIDER_ID)
        except Hostingprovider.DoesNotExist as e:
            logger.warning(f"Hoster Azure not found")
            raise e
            
        assert len(green_ipv4_ranges) > 0
        assert len(green_ipv6_ranges) > 0

        return { 
            "ipv4": self.add_ip_ranges_to_hoster(hoster, green_ipv4_ranges), 
            "ipv6": self.add_ip_ranges_to_hoster(hoster, green_ipv6_ranges)
            }

    def convert_to_networks(self, ip_dataset_with_mask, ip_version = None):
        list_of_networks = set()

        for services in ip_dataset_with_mask['values']:
            for ip_with_mask in services['properties']['addressPrefixes']:
                network = ipaddress.ip_network(ip_with_mask) # Generate network based on ip and subnet mask
                
                if ip_version == None:
                    # If no version is specified: include all
                    list_of_networks.add(network) 
                elif type(network) == ip_version:
                    # Otherwise, include only the specified ip version (IPv4 or IPv6)
                    list_of_networks.add(network)

        return list(list_of_networks)

    def add_ip_ranges_to_hoster(self, hoster, ip_networks):
        results = []
        logger.debug(hoster)
        logger.debug(f"ipnetworks length: {len(ip_networks)}")
        for network in ip_networks:
            res = self.update_hoster(hoster, network[0], network[-1])
            if res:
                results.append(res)

        # TODO: Check for overlapping ranges and remove duplicates
        return results

    def update_hoster(
        self,
        hoster: Hostingprovider,
        first: ipaddress.IPv4Address,
        last: ipaddress.IPv4Address,
    ):
        # use the ORM to update the deets for the corresponding hoster
        # TODO decide if we need to optimise this
        gcip, created = GreencheckIp.objects.update_or_create(
            active=True, ip_start=first, ip_end=last, hostingprovider=hoster
        )
        gcip.save()

        if created:
            logger.debug(gcip)
            return gcip


class Command(BaseCommand):
    help = "Update IP ranges for cloud providers that publish them"

    def handle(self, *args, **options):        
        azure = MicrosoftCloudProvider()
        
        # Retrieve dataset and parse to networks
        dataset = azure.retrieve()
        dataset = azure.process(dataset)

        green_ipv4s = [x for x in dataset if isinstance(x, ipaddress.IPv4Network)]
        green_ipv6s = [x for x in dataset if isinstance(x, ipaddress.IPv6Network)]
        self.stdout.write(
            f"Import Complete: Added {len(green_ipv4s)} new IPV4 networks, "
            f"and {len(green_ipv6s) } IPV6 networks"
        )

