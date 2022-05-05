import pytest
import pathlib
import ipaddress
from io import StringIO

from django.core.management import call_command
from apps.greencheck.management.commands import update_equinix_ip_ranges
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
        archived = False,
        country = "US",
        customer = False,
        icon = "",
        iconurl = "",
        id = settings.EQUINIX_PROVIDER_ID, # host id
        model = "groeneenergie",
        name = "Equinix",
        partner = "",
        showonwebsite = True,
        website = "https://www.equinix.nl",
    )
       
@pytest.fixture
def equinix_cloud_provider(hosting_provider):
    """
    Prepare the cloud provider.
    Return: an initialization of a EquinixCloudProvider object from file update_equinix_ip_ranges.py
    """
    # Propperly initialize the hosting provider so it retrieves necessary values such as an id
    hosting_provider.save() 
    return update_equinix_ip_ranges.EquinixCloudProvider()

@pytest.fixture
def equinix_test_dataset():
    """
    Retrieve a locally saved sample from the population as dataset to use for this test
    Return: list format of the test dataset
    """
    this_file = pathlib.Path(__file__)
    path = this_file.parent.parent.joinpath("fixtures", "equinix_dataset.txt")
    
    list_of_ips = []
    with open(path) as file:
        for line in file.readlines():
            if (line.startswith("AS") or line[0].isdigit()):
                list_of_ips.append(line.split(' ', 1)[0])
                
    return list_of_ips

@pytest.mark.django_db
class TestEquinixCloudImporter:
    def test_dataset_structure(
        self, hosting_provider, equinix_cloud_provider, equinix_test_dataset
    ):
        """
        Test if the structure of the JSON is as expected
        """
        hosting_provider.save() # Initialize hosting provider in database

        # Test: file is in list format after retrieving it
        assert type(equinix_test_dataset) == list and type(equinix_cloud_provider.retrieve_dataset()) == list
        print(len(equinix_test_dataset))

        # Test: check for a list with a single dimension. If more dimensions exist (i.e. another list in the list), throw exception
        assert not isinstance(equinix_test_dataset[0], list) and not isinstance(equinix_cloud_provider.retrieve_dataset()[0], list)

    def test_inserting_range(
        self, hosting_provider, equinix_cloud_provider, equinix_test_dataset
    ):
        """
        Test the insertion of a new range
        """
        ip_ranges = equinix_cloud_provider.convert_to_networks(equinix_test_dataset)
        ip_start, ip_end = ip_ranges[0][0], ip_ranges[0][-1]

        assert GreencheckIp.objects.all().count() == 0  # Test: database is empty
        hosting_provider.save()  # Initialize hosting provider in database

        # As the database is empty, create new range
        equinix_cloud_provider.update_range_in_db(hosting_provider, ip_start, ip_end)

        assert (
            GreencheckIp.objects.all().count() == 1
        )  # Test: contains one value after insertion

    def test_insertion_asn(
        self, hosting_provider, equinix_cloud_provider, equinix_test_dataset
    ):
        """
        Test the insertion of a Autonomous System Number (ASN)
        """
        assert GreencheckASN.objects.all().count() == 0  # Test: database is empty
        hosting_provider.save()  # Initialize hosting provider in database

        # As the database is empty, create new entries for all ASN's
        equinix_cloud_provider.update_asns_in_db(equinix_test_dataset)

        assert (
            GreencheckASN.objects.all().count() == 15
        )  # Test: inserted all 15 ASN's in the test dataset


@pytest.mark.django_db
class TestEquinixImportCommand:
    """
    This just tests that we have a management command that can run.
    We _could_ mock the call to fetch ip ranges, if this turns out to be a slow test.
    """

    def test_handle(self, equinix_cloud_provider):
        out = StringIO()
        call_command("update_equinix_ip_ranges", stdout=out)
        assert "Import Complete:" in out.getvalue()