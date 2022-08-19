import pytest
import pathlib
import ipaddress
import json
from io import StringIO

from django.core.management import call_command
from apps.greencheck.management.commands import update_google_ip_ranges
from apps.accounts.models import Hostingprovider
from apps.greencheck.models import GreencheckIp, GreencheckASN

from django.conf import settings


@pytest.fixture
def hosting_provider():
    """
    Define necessary information of a hosting provider for testing.
    Return: an initialization of a Hostingprovider object
    """
    return Hostingprovider(
        archived=False,
        country="US",
        customer=False,
        icon="",
        iconurl="",
        id=settings.GOOGLE_PROVIDER_ID,  # host id
        model="groeneenergie",
        name="Google",
        partner="",
        showonwebsite=True,
        website="https://www.google.nl",
    )


@pytest.fixture
def google_cloud_provider(hosting_provider):
    """
    Prepare the cloud provider.
    Return: an initialization of a GoogleCloudProvider object from file update_google_ip_ranges.py
    """
    # Propperly initialize the hosting provider so it retrieves necessary values such as an id
    hosting_provider.save()
    return update_google_ip_ranges.GoogleCloudProvider()


@pytest.fixture
def google_test_dataset():
    """
    Retrieve a locally saved sample from the population as dataset to use for this test
    Return: list format of the test dataset
    """
    this_file = pathlib.Path(__file__)
    path = this_file.parent.parent.joinpath("fixtures", "google_dataset.json")

    list_of_ips = []
    with open(path) as file:
        data = json.load(file)
        for prefix in data["prefixes"]:
            list_of_ips.append(list(prefix.values())[0])

    return list_of_ips


@pytest.mark.django_db
class TestGoogleCloudImporter:
    def test_dataset_structure(
        self, hosting_provider, google_cloud_provider, google_test_dataset
    ):
        """
        Test if the structure of the JSON is as expected
        """
        hosting_provider.save()  # Initialize hosting provider in database

        # Test: file is in list format after retrieving it
        assert (
            type(google_test_dataset) == list
            and type(google_cloud_provider.retrieve_dataset()) == list
        )
        print(len(google_test_dataset))

        # Test: check for a list with a single dimension. If more dimensions exist (i.e. another list in the list), throw exception
        assert not isinstance(google_test_dataset[0], list) and not isinstance(
            google_cloud_provider.retrieve_dataset()[0], list
        )

        # Test: check if the list contains either IPv4 or IPv6 networks
        for list_item in google_test_dataset:
            if not isinstance(
                ipaddress.ip_network(list_item),
                (ipaddress.IPv4Network, ipaddress.IPv6Network),
            ):
                assert False

    def test_inserting_range(
        self, hosting_provider, google_cloud_provider, google_test_dataset
    ):
        """
        Test the insertion of a new range
        """
        ip_ranges = google_cloud_provider.convert_to_networks(google_test_dataset)
        ip_start, ip_end = ip_ranges[0][0], ip_ranges[0][-1]

        assert GreencheckIp.objects.all().count() == 0  # Test: database is empty
        hosting_provider.save()  # Initialize hosting provider in database

        # As the database is empty, create new range
        google_cloud_provider.update_range_in_db(hosting_provider, ip_start, ip_end)

        assert (
            GreencheckIp.objects.all().count() == 1
        )  # Test: contains one value after insertion


@pytest.mark.django_db
class TestGoogleImportCommand:
    """
    This just tests that we have a management command that can run.
    We _could_ mock the call to fetch ip ranges, if this turns out to be a slow test.
    """

    def test_handle(self, google_cloud_provider):
        out = StringIO()
        call_command("update_google_ip_ranges", stdout=out)
        assert "Import Complete:" in out.getvalue()
