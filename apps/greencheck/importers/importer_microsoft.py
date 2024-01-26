import logging
from datetime import timedelta
from typing import List, Tuple, Union

import requests
from django.conf import settings
from django.utils import timezone

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
        """
        Fetch the data from the endpoint, returning the parsed json, accounting for the
        Microsoft JSON file having a changing endpoint to fetch from each week.
        """
        status_code = None
        response = None

        fetch_date = timezone.now()
        date_string = fetch_date.strftime("%Y%m%d")

        # we don't want to look further than a week back
        day_count = 0
        DAYS_BACK_LIMIT = 7
        MS_LONG_FETCH_URL_PART = "https://download.microsoft.com/download/7/1/D/71D86715-5596-4529-9B13-DA13A5DE5B63/ServiceTags_Public"

        # We need to try fetching from the endpoint until we get a 200 response, going back a day each
        # time to find the latest json file that is available containing the IP ranges we want

        while status_code != 200:
            ms_ip_range_url = f"{MS_LONG_FETCH_URL_PART}_{date_string}.json"
            logger.info(f"Fetching data from {ms_ip_range_url}")
            response = requests.get(ms_ip_range_url)
            status_code = response.status_code
            logger.info(f"Response was {response}")

            fetch_date = fetch_date - timedelta(days=1)
            date_string = fetch_date.strftime("%Y%m%d")
            day_count += 1

            if day_count > DAYS_BACK_LIMIT:
                logger.warning("Unable to fetch ip range data. Aborting early.")
                break

        try:
            return response.json()
        except requests.RequestException:
            logger.warning("Unable to parse fetched data. Aborting early")

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
