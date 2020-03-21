import json
import requests
import ipaddress
import logging
from apps.greencheck.models import GreencheckIp
from apps.accounts.models import Hostingprovider

from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Update IP ranges for cloud providers that publish them"

    def handle(self, *args, **options):
        pass


class AmazonCloudProvider:

    def __init__(self, *args, **kwargs):
        if kwargs.get('green_regions'):
            self.green_regions = kwargs.get('green_regions')
        else:
            self.green_regions = (
            ('Amazon US West', 'us-west-2', 696),
            ('Amazon EU (Frankfurt)', 'eu-central-1', 697),
            ('Amazon EU (Ireland)', 'eu-west-1', 698),
            ('Amazon AWS GovCloud (USA)','us-gov-west-1', 699),
            ('Amazon Montreal', 'ca-central-1', 700),
        )

    def update_ranges(self):

        iprs = self.fetch_ip_ranges()
        res = []

        for region in self.green_regions:
            _, aws_code, host_id = region

            # pull out the ip ranges as strings
            green_ipv4s = self.pullout_green_regions(iprs, aws_code)
            green_ipv6s = self.pullout_green_regions(iprs, aws_code, ip_version="ipv6")

            hoster = Hostingprovider.objects.get(pk=host_id)

            # then convert them to ip networks
            green_ipv4_ranges = self.ip_ranges_for_hoster(green_ipv4s)
            green_ipv6_ranges = self.ip_ranges_for_hoster(green_ipv6s, ip_version="ipv6")

            assert(len(green_ipv4_ranges) > 0)
            assert(len(green_ipv6_ranges) > 0)

            # we need to do this for ipv4, and then ipv6
            return {
            'ipv4' : self.add_ip_ranges_to_hoster(hoster, green_ipv4_ranges),
            'ipv6' : self.add_ip_ranges_to_hoster(hoster, green_ipv6_ranges),
            }


    def fetch_ip_ranges(self):
        aws_endpoint = "https://ip-ranges.amazonaws.com/ip-ranges.json"
        return requests.get(aws_endpoint).json()

    def pullout_green_regions(self, ip_ranges, region, ip_version=None):
        """
        Returns a list of IP ranges for a given region
        """

        if ip_version == "ipv6":
            prefix = 'ipv6_prefixes'
            aws_lookup_key = "ipv6_prefix"
        else:
            prefix = "prefixes"
            aws_lookup_key = "ip_prefix"

        return [
            aws_ip[aws_lookup_key] for aws_ip in ip_ranges[prefix]
            if aws_ip['region'] == region
        ]


    def ip_ranges_for_hoster(self, ip_ranges, ip_version="ipv4"):
        if ip_version == "ipv6":
            ip_addy = ipaddress.IPv6Network
        else:
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

    def update_hoster(self, hoster: Hostingprovider, first: ipaddress.IPv4Address, last: ipaddress.IPv4Address):
        # use the ORM to update the deets for the corresponding hoster
        gcip, created = GreencheckIp.objects.update_or_create(
            active=True,
            ip_start=first,
            ip_end=last,
            hostingprovider=hoster
        )
        gcip.save()

        if created:
            logger.debug(gcip)
            return gcip