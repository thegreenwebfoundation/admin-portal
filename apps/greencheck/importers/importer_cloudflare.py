import logging
from typing import List, Tuple, Union

import requests
from django.conf import settings

from apps.accounts.models.hosting import Hostingprovider
from apps.greencheck.importers.importer_interface import ImporterProtocol
from apps.greencheck.importers.network_importer import NetworkImporter

logger = logging.getLogger(__name__)


class CloudflareImporter:
    def __init__(self):
        self.hosting_provider_id = settings.CLOUDFLARE_PROVIDER_ID

    def process(self, list_of_addresses: list[str]):
        provider = Hostingprovider.objects.get(id=settings.CLOUDFLARE_PROVIDER_ID)

        network_importer = NetworkImporter(provider)
        network_importer.deactivate_ips()
        network_importer.deactivate_asns()
        return network_importer.process_addresses(list_of_addresses)

    def fetch_data_from_source(self) -> list:
        """
        Fetch the contents of the two cloudflare endpoints, and return a list of 
        IP networks ready to be processed.
        """
        try:
            ipv4_response = requests.get(settings.CLOUDFLARE_REMOTE_API_ENDPOINT_IPV4)
            ipv6_response = requests.get(settings.CLOUDFLARE_REMOTE_API_ENDPOINT_IPV6)
            ipv4_data = ipv4_response.text
            ipv6_data = ipv6_response.text

            # destructure the lines of each text file, to make one longer list
            return *ipv4_data.splitlines(), *ipv6_data.splitlines()
        except requests.RequestException:
            logger.warning("Unable to fetch text files. Aborting early.")

    def parse_to_list(self, raw_data: list[str]) -> List[Union[str, Tuple]]:
        """
        Accept a list of IP networks listed in the remote text file and 
        return a list of IP networks.
        """
        try:
            list_of_ips = []
            for line in raw_data:
                # Filter out empty lines
                if not line:
                    continue

                # (i.e. ip with subnet
                if line.startswith("AS") or line[0].isdigit():
                    list_of_ips.append(line)
            return list_of_ips
        except Exception:
            logger.exception("Something really unexpected happened. Aborting")


assert isinstance(CloudflareImporter(), ImporterProtocol)
