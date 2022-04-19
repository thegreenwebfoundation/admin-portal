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
    # human name in the admin | azure code  | hoster ID
    ("Azure", "azure-code", settings.AZURE_PROVIDER_ID),
)


class MicrosoftCloudProvider:
    # def __init__(self, *args, **kwargs):
    #     if kwargs.get("green_regions"):
    #         self.green_regions = kwargs.get("green_regions")
    #     else:
    #         self.green_regions = GREEN_REGIONS

    #     logger.info(f"Instantiated with {len(self.green_regions)} region(s) to update")

    def update_ranges(self, ip_ranges):
        """
        loop through list of IP ranges, and for each ip range,
        make sure we have a matching green IP range saved in the database
        associatd with this provider
        """
        res = []
        
        # dedupe list of ip range in parsed JSON
        # add/update a greenIP range associate with this host
        # for every IP range in the list from Microsoft
        # save results in database


        # return the list of updates, or created ones
        return res

    def retrieve(self):
        with open('/workspace/admin-portal/apps/greencheck/management/commands/azure-ip-ranges.json') as json_file:
            return json.load(json_file)

        # file = open("azure-ip-ranges.json")
        # return json.load(file)

    def process(self, raw_dataset):
        list_of_ips = []

        """
        loop through list of IP ranges, and for each ip range,
        make sure we have a matching green IP range saved in the database
        associatd with this provider
        """
        green_ipv4s = raw_dataset # did something here in the aws (pull out green ip for regions)
        list_of_ips = self.convert_to_networks(green_ipv4s)

        # dedupe list of ip range in parsed JSON
        # add/update a greenIP range associate with this host
        # for every IP range in the list from Microsoft
        # save results in database

        # return the list of updates, or created ones
        return null

    # Note: This can be a function from a parent class which has the implementation
    def convert_to_networks(self, ip_dataset_with_mask):
        list_of_networks = set()
        for services in ip_dataset_with_mask['values']:
            for ip_with_mask in services['properties']['addressPrefixes']:
                    try:
                        network = ipaddress.ip_network(ip_with_mask) # Generate network based on ip and subnet mask
                        list_of_networks.add(network)

                        print("IP address {} is valid. The object returned is {}".format(ip_with_mask, network))
                    except ValueError:
                        print("IP address {} is not valid".format(ip_with_mask)) 

        return list(list_of_networks)

    def ip_ranges_for_hoster(self, ip_ranges, ip_version="ipv4"):
        """
        accept a list of ip ranges and for each ip range
        crate a network object 'IPv4Network' and 
        """
        # if ip_version == "ipv6":
        #     ip_addy = ipaddress.IPv6Network
        # else:

        # TODO come up with better name than ip_addy
        # `created_ip_addr` ?  
        ip_addy = ipaddress.IPv4Network

        ips_for_hoster = []

        for ipr in ip_ranges:
            network = ip_addy(ipr)

            ips_for_hoster.append(network)

        return ips_for_hoster

    def add_ip_ranges_to_hoster(self, hoster, ip_networks):
        results = []
        logger.debug(hoster)
        logger.debug(f"ipnetworks length: {len(ip_networks)}")
        for network in ip_networks:
            res = self.update_hoster(hoster, network[0], network[-1])
            if res:
                results.append(res)

        return results

    def update_hoster(
        self,
        hoster: Hostingprovider,
        first: ipaddress.IPv4Address,
        last: ipaddress.IPv4Address,
    ):
        # use the ORM to update the deets for the corresponding hoster
        # TODO decide if we need to optimise this
        # 1...................100
        #   5..50
        #           51..70
        gcip, created = GreencheckIp.objects.update_or_create(
            active=True, ip_start=first, ip_end=last, hostingprovider=hoster
        )
        gcip.save()

        if created:
            print('updateded hoster')
            logger.debug(gcip)
            return gcip


class Command(BaseCommand):
    help = "Update IP ranges for cloud providers that publish them"

    def handle(self, *args, **options):
        # 1. Retrieve dataset
        # 2. Parse ip ranges to a usable list
        # 3. Update (by evaluating) our database with the retrieved list
        # 3.1 Log: updated records
        
        azure = MicrosoftCloudProvider()
        
        # Retrieve dataset and parse
        dataset = azure.retrieve()
        dataset = azure.process(dataset)

        # Additional notes:
        # fetch JSON somehw, return list of datastructures for 
        # each ip range given
        # azure.fetch_ip_ranges()

        # update local IP whitelist of green IPs with data 
        # from microsoft list
        # azure.update_ranges(ip_ranges)

        # log the updated IP ranges so we see what has happened

        # for region in update_result:
        #     green_ipv4s, green_ipv6s = region.get("ipv4"), region.get("ipv6")
        #     self.stdout.write(
        #         f"Import Complete: Added {len(green_ipv4s)} new IPV4 addresses, "
        #         f"and {len(green_ipv6s) } IPV6 addresses"
        #     )
