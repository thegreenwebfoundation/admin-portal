import json
import requests
from ipaddress import IPv4Address, IPv6Address
from apps.greencheck.models import GreencheckIp
from apps.accounts.models import Hostingprovider

from django.core.management.base import BaseCommand
from django.db import connection

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

        for region in self.green_regions:
            _, aws_code, host_id = region
            green_ipv4s = self.pullout_green_regions(iprs, region)
            hoster = Hostingprovider.objects.get(pk=host_id)

            self.add_ip_ranges_to_hoster(hoster, green_ipv4s)

        # for region in green_regions:
        #     hoster = self.find_hoster_by_region(region)
        #     self.add_ip_ranges_to_hoster(hoster)

        # we need to do this for ipv4, and then ipv6

        pass

    def fetch_ip_ranges(self):
        aws_endpoint = "https://ip-ranges.amazonaws.com/ip-ranges.json"
        return requests.get(aws_endpoint).json()

    def pullout_green_ips(self, ip_ranges, region, ip_version=None):

        if ip_version == "ipv6":
            prefix = ['ipv6_prefixes']
        else:
            prefix = "prefixes"

        return [
            aws_ip['ip_prefix'] for aws_ip in ip_ranges[prefix]
            if aws_ip['region'] == region
        ]


    def ip_ranges_for_hoster(self, ip_ranges, ip_version="ipv4"):
        if ip_version == "ipv6":
            ip_addy = ipaddress.IPv6Network
        else:
            ip_addy = ipaddress.IPv6Network

        ips_for_hoster = []

        for ipr in ip_ranges:
            network = ip_addy(ipr)
            # first, last = network[0], network[-1]
            ips.append(network)

        return ips_for_hoster


    def update_hoster(self, hoster: Hostingprovider, first: IPv4Address, last: IPv4Address):
        # use the ORM to update the deets for the corresponding hoster
        gcip = GreencheckIp(
            active=True,
            ip_start=first,
            ip_end=last,
            hostingprovider=hoster
        )
        gcip.save()


def ip_ranges_for_hoster(ip_ranges, ip_version="ipv4"):
        if ip_version == "ipv6":
            ip_addy = ipaddress.IPv6Network
        else:
            ip_addy = ipaddress.IPv4Network

        ips_for_hoster = []

        for ipr in ip_ranges:
            network = ip_addy(ipr)

            ips_for_hoster.append(network)

        return ips_for_hoster


def update_hoster(self, hoster: Hostingprovider, ip_range: IPv4Address):
        first, last = ip_range[0], ip_range[-1]
        # use the ORM to update the deets for the corresponding hoster
        return GreencheckIp.update_or_create(
            active=True,
            ip_start=first,
            ip_end=last,
            hostingprovider=hoster
        )

