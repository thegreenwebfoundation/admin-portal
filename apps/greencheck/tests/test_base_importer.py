import pytest
import pathlib
import json
from io import StringIO

from django.core.management import call_command
from apps.greencheck.importers.importer_interface import BaseImporter
from apps.greencheck.models import GreencheckIp, GreencheckASN
from apps.accounts.models import Hostingprovider

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
        id=1234,  # host id
        model="groeneenergie",
        name="General hosting provider",
        partner="",
        showonwebsite=True,
        website="",
    )


@pytest.fixture
def base_importer(hosting_provider: Hostingprovider):
    """
    Initialize a BaseImporter object
    Return: BaseImporter
    """
    importer = BaseImporter(hosting_provider)
    return importer


@pytest.fixture
def sample_data():
    """
    Retrieve a locally saved dataset for testing purposes
    Return: JSON format of the test dataset
    """
    this_file = pathlib.Path(__file__)
    json_path = this_file.parent.parent.joinpath(
        "fixtures", "test_dataset_base_importer.json"
    )
    with open(json_path) as ipr:
        return json.loads(ipr.read())


@pytest.mark.django_db
class TestImporterInterface:
    def test_save_ip(self, hosting_provider, base_importer):
        """
        Test saving IPv4 and IPv6 networks to the database
        """
        testing_ipv4_range = ("191.233.8.25", "191.233.8.30")
        testing_ipv6_range = (
            "2603:1010:0304:0000:0000:0000:0000:0140",
            "2603:1010:0304:0000:0000:0000:0000:015f",
        )
        testing_ipv4_network = "191.233.8.24/29"
        testing_ipv6_network = "2603:1010:304::140/123"

        assert (
            GreencheckIp.objects.all().count() == 0
        )  # Test: database is empty (for IP)
        hosting_provider.save()  # Initialize hosting provider in database

        # Import a single IPv4 network
        base_importer.save_ip(testing_ipv4_range)

        assert (
            GreencheckIp.objects.all().count() == 1
        )  # Test: database is empty (for IP)
        hosting_provider.save()  # Initialize hosting provider in database

        # Import a single IPv4 network
        base_importer.save_ip(testing_ipv6_range)

        assert (
            GreencheckIp.objects.all().count() == 2
        )  # Test: database is empty (for IP)
        hosting_provider.save()  # Initialize hosting provider in database

        # Import a single IPv4 network
        base_importer.save_ip(testing_ipv4_network)

        assert (
            GreencheckIp.objects.all().count() == 3
        )  # Test: IPv4 is saved after insertion

        # Import a single IPv6 network
        base_importer.save_ip(testing_ipv6_network)

        assert (
            GreencheckIp.objects.all().count() == 3
        )  # Test: IPv6 is saved after insertion

    def test_save_asn(self, hosting_provider, base_importer):
        """
        Test saving Autonomous System Numbers (ASN) networks to the database
        """
        testing_asn = "AS27407"

        assert (
            GreencheckASN.objects.all().count() == 0
        )  # Test: database is empty (for ASN)
        hosting_provider.save()  # Initialize hosting provider in database

        # Import a single ASN network
        BaseImporter.save_asn(base_importer, testing_asn)

        assert (
            GreencheckASN.objects.all().count() == 1
        )  # Test: ASN is saved after insertion

    def test_process_addresses(self, hosting_provider, base_importer, sample_data):
        """
        Test processing addresses(IPv4, IPv6 and/or ASN) to save
        a list with various types of networks
        """
        assert (
            GreencheckIp.objects.all().count() == 0
        )  # Test: database is empty (for IP)
        assert (
            GreencheckASN.objects.all().count() == 0
        )  # Test: database is empty (for ASN)
        hosting_provider.save()  # Initialize hosting provider in database

        # Process list of addresses in JSON file
        
        base_importer.process_addresses(sample_data)

        assert (
            GreencheckIp.objects.all().count() == 63
            and GreencheckASN.objects.all().count() == 5
        )  # Test: list of IPv4,IPv6 and ASN is saved after insertion
