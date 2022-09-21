import logging
import requests

from datetime import datetime, timedelta
from django.conf import settings
from . import object_storage


logger = logging.getLogger(__name__)


class MicrosoftBucketUpdater:
    def __init__(self):
        self.url_prefix = "https://download.microsoft.com/download/7/1/D/71D86715-5596-4529-9B13-DA13A5DE5B63/ServiceTags_Public_"
        self.url_file_extension = ".json"

    def search_dataset(self) -> dict:
        """
        Searches for a working url from Microsoft's endpoint.
        If a dataset is found, it will be returned by this function.
        Return: dict
        """
        date_to_check = datetime.now()
        date_threshold = datetime.now() - timedelta(days=5)

        # Iterate through the days to find a working
        # endpoint that returns a dataset
        while date_to_check >= date_threshold:
            response = requests.get(self.format_date_to_url(date_to_check))

            if response.status_code == 200:
                return response.json()
            else:
                # Keep searching if no dataset is found
                date_to_check = date_to_check - timedelta(days=1)

        return None

    def update_bucket(self):
        """
        Updates bucket after finding a dataset
        """
        dataset = self.search_dataset()
        # TODO: Is this the right name of the file?
        # file_name = settings.MICROSOFT_REMOTE_FILE_DIRECTORY
        file_name = "data-imports/ms-azure-ip-ranges-2022-04-25.json"

        if dataset:
            object_storage.bucket_file_put_json(
                settings.DOMAIN_SNAPSHOT_BUCKET, dataset, file_name
            )

    def format_url_to_date(self, url: str) -> datetime:
        """
        Format a url string to datetime format
        """
        return url[len(self.url_prefix) : len(url) - len(self.url_file_extension)]

    def format_date_to_url(self, date: datetime) -> str:
        """
        Format a datetime to url string format
        """
        return self.url_prefix + date.strftime("%Y%m%d") + self.url_file_extension
