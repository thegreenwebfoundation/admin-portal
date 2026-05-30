import logging
from typing import List, Tuple, Union

import requests
from django.conf import settings

from apps.accounts.models import Hostingprovider
from apps.greencheck.importers.importer_interface import ImporterProtocol
from apps.greencheck.importers.network_importer import NetworkImporter

logger = logging.getLogger(__name__)


class GoogleImporter:
    def fetch_data_from_source(self):
        try:
            response = requests.get(settings.GOOGLE_DATASET_ENDPOINT)
            return response.json()
        except requests.RequestException:
            logger.warning("Unable to fetch file. Aborting early.")
        except Exception:
            logger.exception("Something really unexpected happened. Aborting")

    def parse_to_list(self, raw_data) -> List[Union[str, Tuple]]:
        """
        Convert the parsed data into a list of either IP Ranges
        """
        list_of_ips = []

        # Loop through IPv4 addresses
        for addressDict in raw_data["prefixes"]:
            if "ipv4Prefix" in addressDict.keys():
                list_of_ips.append(addressDict.get("ipv4Prefix"))
            elif "ipv6Prefix" in addressDict.keys():
                list_of_ips.append(addressDict.get("ipv6Prefix"))
        # This provider only has IPv4 and IPv6, so we
        # don't have to look for ASNs here
        return list_of_ips

    def process(self, list_of_addresses):
        provider = Hostingprovider.objects.get(id=settings.GOOGLE_PROVIDER_ID)

        network_importer = NetworkImporter(provider)
        network_importer.deactivate_ips()
        return network_importer.process_addresses(list_of_addresses)


assert isinstance(GoogleImporter(), ImporterProtocol)
