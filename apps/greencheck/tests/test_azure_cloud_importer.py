import pytest
import pathlib
import ipaddress
import json
from io import StringIO

from django.core.management import call_command
from apps.greencheck.management.commands import update_azure_ip_ranges
from apps.accounts.models import Hostingprovider
from apps.greencheck.models import GreencheckIp

from django.conf import settings


@pytest.fixture
def hosting_provider():
    """
    Define necessary information of a hosting provider for testing.
    Return: an initialization of a Hostingprovider object 
    """
    return Hostingprovider(
        archived = False,
        country = "US",
        customer = False,
        icon = "",
        iconurl = "",
        id = settings.AZURE_PROVIDER_ID, # host id
        model = "groeneenergie",
        name = "Azure US West",
        partner = "",
        showonwebsite = True,
        website = "http://azure.microsoft.com",
    )


@pytest.fixture
def azure_cloud_provider(hosting_provider):
    """
    Prepare the cloud provider.
    Return: an initialization of a MicrosoftCloudProvider object from file update_azure_ip_ranges.py
    """
    # Propperly initialize the hosting provider so it retrieves necessary values such as an id
    hosting_provider.save() 
    return update_azure_ip_ranges.MicrosoftCloudProvider()


@pytest.fixture
def azure_test_dataset():
    """
    Retrieve a locally saved sample from the population as dataset to use for this test
    Return: JSON format of the test dataset
    """
    this_file = pathlib.Path(__file__)
    json_path = this_file.parent.parent.joinpath("fixtures", "azure_ip_ranges.json")
    with open(json_path) as ipr:
        return json.loads(ipr.read())


@pytest.mark.django_db
class TestAZURECLoudImporter:
    def test_dataset_structure(self, hosting_provider, azure_cloud_provider):
        """
        Test if the structure of the JSON is as expected
        """
        hosting_provider.save()  # Initialize hosting provider in database
        dataset = azure_cloud_provider.retrieve_dataset()

        # Test: structure contains the main three keys
        assert len(dataset.keys()) == 3

        # Test: fields are available for traversing 
        assert dataset['values'][0]['properties']['addressPrefixes']
        
    def test_inserting_range(self, hosting_provider, azure_cloud_provider):
        """
        Test the insertion of a new range
        """
        _, host_id = ("Azure", settings.AZURE_PROVIDER_ID)

        dataset = azure_cloud_provider.retrieve_dataset()
        ip_ranges = azure_cloud_provider.convert_to_networks(dataset)
        ip_start, ip_end = ip_ranges[0][0], ip_ranges[0][-1]

        assert GreencheckIp.objects.all().count() == 0 # Test: database is empty 
        hosting_provider.save() # Initialize hosting provider in database

        # As the database is empty, create new range
        azure_cloud_provider.update_range_in_db(hosting_provider, ip_start, ip_end)
        
        assert GreencheckIp.objects.all().count() == 1 # Test: contains one value after insertion

    def test_extract_ip_ranges(
        self, hosting_provider, azure_cloud_provider, azure_test_dataset
    ):
        """
        Test extracting ip ranges from dataset and saving in dataset.
        """
        assert GreencheckIp.objects.all().count() == 0 # Test: database is empty 
        hosting_provider.save() # Initialize hosting provider in database

        ip_ranges = azure_cloud_provider.extract_ip_ranges(azure_test_dataset)
        ipv4s = ip_ranges["ipv4"]
        ipv6s = ip_ranges["ipv6"]

        # Test : correct number of ips are extracted from the test dataset
        assert len(ipv4s) == 649
        assert len(ipv6s) == 146

        # Test: database has equal altercation in comparison to the returned dataset
        # This value should equate to 795 in total 
        assert GreencheckIp.objects.all().count() == len(ipv4s) + len(ipv6s)


@pytest.mark.django_db
class TestAZUREImportCommand:
    """
    This just tests that we have a management command that can run.
    We _could_ mock the call to fetch ip ranges, if this turns out to be a slow test.
    """

    def test_handle(self, azure_cloud_provider):
        out = StringIO()
        call_command("update_azure_ip_ranges", stdout=out)
        assert "Import Complete:" in out.getvalue()
