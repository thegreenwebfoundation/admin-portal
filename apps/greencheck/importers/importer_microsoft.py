import logging
from typing import List, Tuple, Union

import requests
from django.conf import settings

from apps.accounts.models.hosting import Hostingprovider
from apps.greencheck.importers.importer_interface import ImporterProtocol
from apps.greencheck.importers.network_importer import NetworkImporter

logger = logging.getLogger(__name__)


class MicrosoftImporter:
    def process(self, list_of_addresses):
        provider = Hostingprovider.objects.get(id=settings.MICROSOFT_PROVIDER_ID)

        network_importer = NetworkImporter(provider)
        network_importer.deactivate_ips()
        return network_importer.process_addresses(list_of_addresses)

    def fetch_data_from_source(self) -> list:
        try:
            response = requests.get(settings.MICROSOFT_LOCAL_FILE_DIRECTORY)
            return response.json()
        except requests.RequestException:
            logger.warning("Unable to fetch ip range data. Aborting early.")

    def parse_to_list(self, raw_data) -> List[Union[str, Tuple]]:
        list_of_ips = []

        # Extract IPv4 and IPv6
        for services in raw_data["values"]:
            for address in services["properties"]["addressPrefixes"]:
                list_of_ips.append(address)

        # This provider only has IPv4 and IPv6, so we
        # don't have to include ASN here
        return list_of_ips


assert isinstance(MicrosoftImporter(), ImporterProtocol)
