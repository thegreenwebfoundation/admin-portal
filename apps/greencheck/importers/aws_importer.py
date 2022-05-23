import requests
import logging

from apps.greencheck.importers.importer_interface import BaseImporter, Importer

from django.conf import settings

logger = logging.getLogger(__name__)

class AwsImporter(BaseImporter):
    def __init__(cls):
        cls.hosting_provider_id = settings.AWS_PROVIDER_ID

    def fetch_data_from_source(cls) -> list:
        try:
            response = requests.get(settings.AWS_DATASET_ENDPOINT).json()
            return cls.parse_to_list(response)
        except requests.RequestException:
            logger.warning("Unable to fetch text file. Aborting early.")

    def parse_to_list(cls, raw_data) -> list:
        try:
            list_of_ips = []

            # Loop through IPv4 addresses
            for address in raw_data['prefixes']:
                list_of_ips.append(address['ip_prefix'])

            # Loop through IPv6 addresses
            for address in raw_data['ipv6_prefixes']:
                list_of_ips.append(address['ipv6_prefix'])

            # This provider only has IPv4 and IPv6, so we
            # don't have to include ASN here
            return list_of_ips
        except Exception as e:
            logger.exception("Something really unexpected happened. Aborting")