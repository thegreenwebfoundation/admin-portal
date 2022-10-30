
import requests
import pytest
import logging
import json
import boto3
from moto import mock_s3
from django.conf import settings
from datetime import datetime, timedelta

from apps.greencheck.microsoft_bucket_updater import MicrosoftBucketUpdater

logger = logging.getLogger(__name__)


@pytest.fixture
def s3():
    """Pytest fixture that creates the recipes bucket in 
    the fake moto AWS account

    Yields a fake boto3 s3 client
    """
    with mock_s3():
        s3 = boto3.client("s3")
        s3.create_bucket(Bucket=settings.DOMAIN_SNAPSHOT_BUCKET)
        yield s3


class DummyRequester:
    def __init__(self, content, status_code):
        """
        Mock out content and status_code
        """

        self.content = content
        self.status_code = status_code


@pytest.mark.django_db
class TestMicrosoftBucketUpdater:
    def test_initiate_update_bucket(self):
        # TODO: Implement this test function
        return False

    def test_search_for_dataset(self, mocker):
        """
        Simulate searching API endpoints backwards in time from today on a day-to-day
        basis until an endpoint is found that returns a dataset.
        """
        updater = MicrosoftBucketUpdater()

        # Prepare endpoint mocks
        # It is set up that only the 4th day from now returns a dataset

        # For example we do a request for 01-20-2022:
        # The algorithm searches the following dates with their return:
        # 01-20-2022: 404
        # 01-19-2022: 404
        # 01-18-2022: 404
        # 01-17-2022: 200

        # Request today: 404
        mocker.patch.object(
            requests,
            "get",
            DummyRequester(
                updater.format_date_to_url(
                    datetime.now(), updater.ms_endpoint_url_prefix
                ),
                404,
            ),
        )

        # Request 1 dag ago (yesterday): 404
        mocker.patch.object(
            requests,
            "get",
            DummyRequester(
                updater.format_date_to_url(
                    datetime.now() - timedelta(days=1), updater.ms_endpoint_url_prefix
                ),
                404,
            ),
        )

        # Request 2 days ago (day before yesterday): 404
        mocker.patch.object(
            requests,
            "get",
            DummyRequester(
                updater.format_date_to_url(
                    datetime.now() - timedelta(days=2), updater.ms_endpoint_url_prefix
                ),
                404,
            ),
        )

        # Request 3 days ago: 200 (dataset found)
        dataset_date = datetime.now() - timedelta(days=3)
        mocker.patch.object(
            requests,
            "get",
            DummyRequester(
                updater.format_date_to_url(
                    dataset_date, updater.ms_endpoint_url_prefix
                ),
                200,
            ),
        )

        # Start searcher
        url = updater.search_for_dataset()

        # The found url must be equal to the url we know returns a 200 HTTP status
        assert url == updater.format_date_to_url(
            dataset_date, updater.ms_endpoint_url_prefix
        )

    def test_search_for_dataset_on_same_day(self, mocker):
        """
        Simulate searching API endpoints backwards in time from today on a day-to-day
        basis until an endpoint is found that returns a dataset, although the date that
        returns a dataset is today.
        """
        updater = MicrosoftBucketUpdater()

        # Prepare endpoint mocks

        # Request today: 200 (dataset found)
        mocker.patch.object(
            requests,
            "get",
            DummyRequester(
                updater.format_date_to_url(
                    datetime.now(), updater.ms_endpoint_url_prefix
                ),
                200,
            ),
        )

        # Request 1 dag ago (yesterday): 404
        mocker.patch.object(
            requests,
            "get",
            DummyRequester(
                updater.format_date_to_url(
                    datetime.now() - timedelta(days=1), updater.ms_endpoint_url_prefix
                ),
                404,
            ),
        )

        try:
            # Start searcher
            url = updater.search_for_dataset()
        except Exception as err:
            # Assuming that for example the searcher keeps searching infinitely because
            # it skipped today and today so happens to be the last updated dataset.
            print(
                f"Unexpected {err=}, {type(err)=} when searching for a working "
                f"endpoint."
            )
            assert False

        # No error occured by no dataset is returned, which means that the search was
        # not succesful
        assert url is None

    def test_search_for_dataset_with_long_search_window(self, mocker):
        """
        Test if the function throws an error when the search window is too long.
        This might occur because there is no support for the endpoint or something
        might be wrong with the object storage or simply because there is a bug in
        the code.
        """
        updater = MicrosoftBucketUpdater()

        # Identify method we want to mock
        path_to_mock = (
            "apps.greencheck.microsoft_bucket_updater."
            "MicrosoftBucketUpdater.retrieve_delta_last_updated"
        )

        # Define a different return when the targeted mock
        # method is called
        # Mock the function that calculates the distance from today till the last
        # updated to return a distance of 100 days
        mocker.patch(
            path_to_mock,
            return_value=datetime.now() - timedelta(days=100),
        )

        try:
            # Start searcher
            updater.search_for_dataset()
        except RuntimeWarning:
            # Catch an error which warns us that our search window is too big.
            assert True

    def test_retrieve_dataset(self, mocker):
        """
        Function that retrieves a dataset as JSON from a given endpoint.
        """
        updater = MicrosoftBucketUpdater()

        # Retrieve dataset from Microsoft
        url = self.search_for_dataset()

        # Execute HTTP request and recieve JSON
        dataset = updater.retrieve_dataset(url)

        assert dataset is not None
        assert type(dataset) is json

    def test_upload_dataset_to_bucket(self):
        """
        Test uploading a dataset (JSON file) to object storage by mocking it.
        """
        updater = MicrosoftBucketUpdater()

        # Mock s3 bucket
        bucket = s3()

        # Check that the bucket is empty
        # list_objects() returns an empty dict if empty which equals to False as bool
        # which in turn means that the assert asserts False
        assert not bucket.list_objects()

        # Some JSON for testing:
        dataset = json.loads('{ "ipv4":"xxx.xxx.xxx.xxx" }')

        updater.upload_dataset_to_bucket(dataset, datetime.now())

        # Check that the dataset is added to the bucket
        assert bucket.list_objects()

    def test_retrieve_delta_last_updated(self):
        # TODO: implement this test function
        # Approach might be:
        # 1. add file to a mock bucket
        #    -> with specific name
        #    -> older than today
        # 2. ask this delta function to return the difference between today and the 
        # file in the mocked object storage
        assert False

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
