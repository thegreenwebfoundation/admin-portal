import requests
import logging
import json
from datetime import datetime, timedelta
from . import object_storage


class MicrosoftBucketUpdater:
    def __init__(self):
        self.ms_endpoint_url_prefix = """https://download.microsoft.com/download/7/1/D/
        71D86715-5596-4529-9B13-DA13A5DE5B63/ServiceTags_Public_"""
        self.bucket_url_prefix = "data-imports/microsoft-network-ranges-"
        self.file_extension = ".json"

    def initiate_update_bucket(self) -> bool:
        """
        Initiate the process of searching, retrieving and uploading the latest version
        of Microsof's dataset containing all active network ranges.

        Return bool: True when the full process was successful, False otherwise
        """
        # Search
        url = self.search_for_dataset()

        if url:
            # Retrieve
            dataset = self.retrieve_dataset(url)

            # Upload
            return self.upload_dataset_to_bucket(
                dataset, self.format_url_to_date(url, self.bucket_url_prefix)
            )
        else:
            logging.error(
                "Microsoft bucket updater: No newer dataset found on the server."
            )
            return False

    def search_for_dataset(self) -> str:
        """
        Searching Microsoft's server for an endpoint that returns a dataset containing
        active network (IP/ASN) ranges.

        Searching is being done by doing a HTTP request to a specific address and
        trying out different dates at the ending of this address.

        The reason for searching backwards in time is to ensure to always get the
        latest version of the dataset first, in the case of having multiple endpoints
        active at once.

        Return str: Representing a url from Microsoft that returns a dataset
        containing active IP ranges
        """
        # Set a range to start searching from:
        # - pivot : iterable date, starting with today
        # - until : date to search up to (difference between today and last updated)
        date_pivot = datetime.now()
        duration_between_last_updated = self.retrieve_delta_last_updated()
        date_until = date_pivot - duration_between_last_updated

        if date_until > 30:
            raise RuntimeWarning(
                """Searching window is abnormally big. Endpoint is 
            either not showing support or something else might be wrong."""
            )

        # Return the value of delta given that it is greater or equal than one day
        # If an update already occurred within the 24hours of now, then return one day

        # Search backwards through Microsoft's addresses with a different date appended
        # at the end of the url.

        # Search backwards in time by trying out addresses with a specific ending date
        # postfixed
        # The search is succesful when a working endpoint is found and returned.
        while (date_pivot >= date_until) and duration_between_last_updated > timedelta(
            days=1
        ):
            tmp_url = self.format_date_to_url(date_pivot, self.ms_endpoint_url_prefix)
            response = requests.get(tmp_url)

            if response.status_code == 200:
                # Dataset found
                return tmp_url
            else:
                # No dataset found:
                # move the pivot and try the day before that
                date_pivot = date_pivot - timedelta(days=1)

        return None

    def retrieve_dataset(self, url) -> json:
        """
        Retrieve the dataset from a given url.

        Return json: Containing the data
        """
        response = requests.get(url)
        return response.json()

    def upload_dataset_to_bucket(self, dataset, date: datetime()) -> bool:
        """
        Uploads a given dataset to the bucket.
        This dataset represents the network (IP/ASN) ranges from the hosting provider.

        Return bool: True if successfully uploaded, False otherwise
        """
        # TODO: remove personal creds
        bucket_name = "roald-testing-bucket"
        data = dataset["data"]
        file_name = self.format_date_to_url(date, self.bucket_url_prefix)

        # TODO: Test if this function works
        return object_storage.upload_file_to_bucket(data, file_name, bucket_name)

    def retrieve_delta_last_updated(self) -> timedelta:
        """
        Get the difference between today and the day that the object storage file was
        last updated as timedelta

        This method retrieves this date by fetching the file from object storage and
        extracting its date from the name. From today's date the delta is being
        calculated.

        Knowing the difference between these dates is particularly useful for knowing
        how far we can search back and get a updated version. Searching further than
        that (today - delta) only retrieves an outdated version of the dataset.

        Return timedelta: The time between today and the last updated object in
        object storage
        """
        # Get bucket and retrieve items that match the prefix of the file
        bucket = object_storage.bucket_green_domains()
        object_collection = bucket.objects.filter(Prefix=self.bucket_url_prefix)

        # Use matches as follows:
        # 1. use first match
        # 2. extract date from file name
        # 3. convert to date object and return
        for single_object in object_collection:
            last_updated = self.format_url_to_date(
                single_object.key, self.bucket_url_prefix
            )

            # Return the duration between today and the date it was last updated
            return datetime.now() - last_updated

    def format_url_to_date(self, url: str, url_prefix: str) -> datetime:
        """
        Format an url str to datetime format given a prefix

        Return datetime: Representing the extracted date
        """
        return datetime.strptime(
            url[len(url_prefix) : len(url) - len(self.file_extension)], "%Y%m%d"
        )

    def format_date_to_url(self, date: datetime, url_prefix: str) -> str:
        """
        Format a datetime to a string format that follows the servers pattern

        Return str: Representing an url to execute a HTTP request on
        """
        return url_prefix + date.strftime("%Y%m%d") + self.file_extension
