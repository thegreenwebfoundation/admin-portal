import logging
from typing import List, Tuple, Union

import requests
from django.conf import settings

from apps.accounts.models.hosting import Hostingprovider
from apps.greencheck.importers.importer_interface import ImporterProtocol
from apps.greencheck.importers.network_importer import NetworkImporter

logger = logging.getLogger(__name__)


class EquinixImporter:
    def __init__(cls):
        cls.hosting_provider_id = settings.EQUINIX_PROVIDER_ID

    def process(self, list_of_addresses):
        provider = Hostingprovider.objects.get(id=settings.EQUINIX_PROVIDER_ID)

        network_importer = NetworkImporter(provider)
        network_importer.deactivate_ips()
        network_importer.deactivate_asns()
        return network_importer.process_addresses(list_of_addresses)

    def fetch_data_from_source(cls) -> list:
        try:
            response = requests.get(settings.EQUINIX_REMOTE_API_ENDPOINT)
            return response.text
        except requests.RequestException:
            logger.warning("Unable to fetch text file. Aborting early.")

    def parse_to_list(self, raw_data) -> List[Union[str, Tuple]]:
        try:
            list_of_ips = []
            for line in raw_data.splitlines():
                # Filter out the lines with network information
                # (i.e. ip with subnet or AS numbers)
                if line.startswith("AS") or line[0].isdigit():
                    list_of_ips.append(
                        line.split(" ", 1)[0]
                    )  # Format as follows: IP range/ASN, Naming

            return list_of_ips
        except Exception:
            logger.exception("Something really unexpected happened. Aborting")


assert isinstance(EquinixImporter(), ImporterProtocol)
