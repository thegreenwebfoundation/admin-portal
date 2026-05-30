import logging
from typing import List, Tuple, Union

import requests
from django.conf import settings

from apps.accounts.models.hosting import Hostingprovider
from apps.greencheck.importers.importer_interface import ImporterProtocol
from apps.greencheck.importers.network_importer import NetworkImporter

logger = logging.getLogger(__name__)


class AmazonImporter:
    """
    An importer that consumes a set of IP ranges from Amazon's AWS endpoint,
    and updates the database with the new IP ranges for each region for the
    provider
    """

    green_regions = [
        "us-east-1",  # N Virginia and matching Govcloud
        "us-east-2",  # Ohio
        "us-west-1",  # Oregon and matching Govcloud
        "us-west-2",  # N. California
        "ca-central-1",  # Canada
        "eu-west-1",  # Ireland
        "eu-west-2",  # London
        "eu-west-3",  # Paris
        "eu-central-1",  # Frankfurt
        "eu-central-2",  # Zurich
        "eu-north-1",  # Stockholm
        "eu-south-1",  # Milan
        "eu-south-2",  # Spain
        "ap-south-1",  # Mumbai
        "ap-south-2",  # Hyperabad
        # TODO: China Bejing and Ningxia too
        # (what is their region code?)
    ]

    def process(self, list_of_addresses):
        provider = Hostingprovider.objects.get(id=settings.AMAZON_PROVIDER_ID)

        network_importer = NetworkImporter(provider)
        network_importer.deactivate_ips()
        return network_importer.process_addresses(list_of_addresses)

    def fetch_data_from_source(self) -> dict:
        """
        Fetch the data from the endpoint, returning the parsed json
        """
        try:
            response = requests.get(settings.AMAZON_REMOTE_API_ENDPOINT)
            return response.json()
        except requests.RequestException:
            logger.warning("Unable to fetch ip data. Aborting early.")

    # fill in the type signature to be a list of either IP Networks, or AS names
    def parse_to_list(self, raw_data) -> List[Union[str, Tuple]]:
        """
        Convert the parsed data into a list of either IP Ranges
        """

        green_ipv4_ranges = [
            ip_range
            for ip_range in raw_data["prefixes"]
            if ip_range["region"] in self.green_regions
        ]

        green_ipv6_ranges = [
            ip_range
            for ip_range in raw_data["ipv6_prefixes"]
            if ip_range["region"] in self.green_regions
        ]
        try:
            list_of_ips = []

            # Loop through IPv4 addresses
            for address in green_ipv4_ranges:
                list_of_ips.append(address["ip_prefix"])

            # Loop through IPv6 addresses
            for address in green_ipv6_ranges:
                list_of_ips.append(address["ipv6_prefix"])

            # This provider only has IPv4 and IPv6, so we
            # don't have to include ASN here
            return list_of_ips
        except Exception as ex:
            logger.exception(
                f"Something really unexpected happened. Exception was: {ex}"
            )


assert isinstance(AmazonImporter(), ImporterProtocol)
