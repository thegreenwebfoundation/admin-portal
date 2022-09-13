import logging
import boto3
import requests

from datetime import datetime, timedelta
from django.conf import settings

logger = logging.getLogger(__name__)


class MicrosoftBucketUpdater:
    def __init__(self):
        self.url_prefix = "https://download.microsoft.com/download/7/1/D/71D86715-5596-4529-9B13-DA13A5DE5B63/ServiceTags_Public_"
        self.url_file_extension = ".json"

    def search_dataset(self, date_to_check: datetime) -> dict:
        """
        Searches for a working url from Microsoft's endpoint.
        If it returns data, this function will return this as a dict.
        """
        date_threshold = datetime.now() - timedelta(days=5)

        while date_to_check >= date_threshold:
            response = requests.get(self.format_date_to_url(date_to_check))

            if response.status_code == 200:
                return response.json()
            else:
                # No dataset found?
                # Keep searching by looking at previous days
                date_to_check = date_to_check - timedelta(days=1)

    def update_bucket(self):
        """
        Saves and updates a bucket, so this data can later on be retrieved by the importer.
        """
        dataset = self.search_dataset()

        # Retrieve resource
        session = boto3.Session(region_name=settings.OBJECT_STORAGE_REGION)
        resource = session.resource(
            "s3",
            endpoint_url=settings.OBJECT_STORAGE_ENDPOINT,
            aws_access_key_id=settings.OBJECT_STORAGE_ACCESS_KEY_ID,
            aws_secret_access_key=settings.OBJECT_STORAGE_SECRET_ACCESS_KEY,
        )

        # TODO: list all buckets for now, remove later
        for bucket in resource.bucket.all():
            logger.info(bucket.name)
        # TODO: Remove plan below
        # 1. Get resource
        # 2. Check if bucket is there, otherwise create it
        # 3. Update bucket data with the dataset recieved

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