import pytest
import logging
from datetime import datetime, timedelta
import requests

from apps.greencheck.microsoft_bucket_updater import MicrosoftBucketUpdater

logger = logging.getLogger(__name__)


class GoGetter:
    """
    The thing I am testing, this is usually imported into the test file, but
    defined here for simplicity.
    """

    def get(self):
        """
        Get the content of `https://waylonwalker.com` and return it as a string
        if successfull, or False if it's not found.
        """
        r = requests.get("https://waylonwalker.com")
        if r.status_code == 200:
            return r.content
        if r.status_code == 404:
            return False


class DummyRequester:
    def __init__(self, content, status_code):
        """
        Mock out content and status_code
        """

        self.content = content
        self.status_code = status_code

    def __call__(self, url):
        """
        The way I set this up GoGetter is going to call an instance of this
        class, so the easiest way to make it work was to implement __call__.
        """
        self.url = url
        return self


@pytest.mark.django_db
class TestMicrosoftBucketUpdater:
    def test_initiate_update_bucket(self):
        # TODO: Implement this test function
        return False

    def test_search_for_dataset(self, mocker):
        """"
        Test the search functionality for finding a endpoint in Microsoft's server by 
        simulating it
        """
        # TODO: Test this test function
        updater = MicrosoftBucketUpdater()

        # Create mocks to simulate searching back through the dates
        # Request today: 404
        mocker.patch.object(requests, "get", DummyRequester(
            updater.format_date_to_url(datetime.now()), 404)
        )

        # Request 1 dag ago (yesterday): 404
        mocker.patch.object(requests, "get", DummyRequester(
            updater.format_date_to_url(datetime.now() - timedelta(days=1)), 404)
        )

        # Request 2 days ago (day before yesterday): 404
        mocker.patch.object(requests, "get", DummyRequester(
            updater.format_date_to_url(datetime.now() - timedelta(days=2)), 404)
        )

        # Request 3 days ago: 200 (dataset found!)
        dataset_date = datetime.now() - timedelta(days=3)
        mocker.patch.object(requests, "get", DummyRequester(
            updater.format_date_to_url(dataset_date), 200)
        )

        # Start the searching process
        url = updater.search_for_dataset()

        # The found url must be equal to the url we know returns a 200 HTTP status
        assert url == updater.format_date_to_url(
                dataset_date,
                updater.ms_endpoint_url_prefix
            )

        # TODO Things to test:
        # - what happens when the duration between today and last updated is less than 1 day

        return False

    def test_retrieve_dataset(self, mocker):
        updater = MicrosoftBucketUpdater()
        # TODO: Implement this test function
        dataset_date = datetime.now() - timedelta(days=3)
        mocker.patch.object(requests, "get", DummyRequester(
            updater.format_date_to_url(dataset_date), 200)
        )

        return False

    def test_upload_dataset_to_bucket(self):
        # TODO To test:
        # - if object storage is being updated
        # TODO: Implement this test function
        
        # TODO: check bucket and see if it is updated
        # Can't do the following:
        # 1. get file
        # 2. run updater
        # 3. get file again and compare
        # Because it does not necessarily update very time
        # Solution: check if the changed date of the file has changed in the bucket

        return False

    def test_retrieve_delta_last_updated(self):
        # TODO: Implement this test function
        return False

    def test_format_url_to_date(self):
        """
        Test formatting from url to date
        """
        updater = MicrosoftBucketUpdater()

        # TODO: an error occurs when I try to run this
        # It throws an error: now() is not an attribute of datetime
        # assuming this might be overwritten by a custom function
        date = datetime.now().strftime("%Y%m%d")
        url = updater.url_prefix + date + updater.url_file_extension

        # Use formatting function
        updater_date = updater.format_url_to_date(url)

        assert date == updater_date

    def test_format_date_to_url(self):
        """
        Test formatting from date to url
        """
        updater = MicrosoftBucketUpdater()

        date = datetime.now()
        # TODO: an error occurs when I try to run this
        # It throws an error: now() is not an attribute of datetime
        # assuming this might be overwritten by a custom function
        url = (
            f"{updater.url_prefix}{date.strftime('%Y%m%d')}{updater.url_file_extension}"
        )

        # Use formatting function
        updater_url = updater.format_date_to_url(date)

        assert url == updater_url
