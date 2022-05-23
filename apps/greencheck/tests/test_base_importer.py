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
def base_importer():
    """
    Initialize a BaseImporter object
    Return: BaseImporter
    """
    importer = BaseImporter
    importer.hosting_provider_id = 1234
    return importer


@pytest.fixture
def sample_data():
    """
    Retrieve a locally saved dataset for testing purposes
    Return: JSON format of the test dataset
    """
    this_file = pathlib.Path(__file__)
    json_path = this_file.parent.parent.joinpath(
        "fixtures", "base_importer_dataset.json"
    )
    with open(json_path) as ipr:
        return json.loads(ipr.read())


@pytest.mark.django_db
class TestImporterInterface:
    def test_save_ip(self, hosting_provider, base_importer):
        """
        Test saving IPv4 and IPv6 networks to the database
        """
        testing_ipv4 = "191.233.8.24/29"
        testing_ipv6 = "2603:1010:304::140/123"

        assert (
            GreencheckIp.objects.all().count() == 0
        )  # Test: database is empty (for IP)
        hosting_provider.save()  # Initialize hosting provider in database

        # Import a single IPv4 network
        BaseImporter.save_ip(base_importer, testing_ipv4)

        assert (
            GreencheckIp.objects.all().count() == 1
        )  # Test: IPv4 is saved after insertion

        # Import a single IPv6 network
        BaseImporter.save_ip(base_importer, testing_ipv6)

        assert (
            GreencheckIp.objects.all().count() == 2
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
        BaseImporter.process_addresses(base_importer, sample_data)

        assert (
            GreencheckIp.objects.all().count() == 63
            and GreencheckASN.objects.all().count() == 5
        )  # Test: list of IPv4,IPv6 and ASN is saved after insertion
