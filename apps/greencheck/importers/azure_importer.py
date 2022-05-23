import requests
import logging

from apps.greencheck.importers.importer_interface import BaseImporter, Importer

from django.conf import settings

logger = logging.getLogger(__name__)

class AzureImporter(BaseImporter):
    def __init__(cls):
        cls.hosting_provider_id = settings.AZURE_PROVIDER_ID

    def fetch_data_from_source(cls) -> list:
        try:
            response = requests.get(settings.AZURE_DATASET_ENDPOINT).json()
            return cls.parse_to_list(response)
        except requests.RequestException:
            logger.warning("Unable to fetch text file. Aborting early.")

    def parse_to_list(cls, raw_data) -> list:
        try:
            list_of_ips = []

            # Extract IPv4 and IPv6
            for services in raw_data["values"]:
                for address in services["properties"]["addressPrefixes"]:
                    list_of_ips.append(address)

            # This provider only has IPv4 and IPv6, so we
            # don't have to include ASN here
            return list_of_ips
        except Exception as e:
            logger.exception("Something really unexpected happened. Aborting")