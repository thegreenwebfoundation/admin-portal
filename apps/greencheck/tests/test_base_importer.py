import pytest
import pathlib
import json
from io import StringIO
import pdb

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
def asn_list():
    """
    Define a list of Autonomous System(AS) Numbers for testing.
    Return: a list of ASN's
    """




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
        "fixtures", "test_dataset_base_importer.json"
    )
    with open(json_path) as ipr:
        return json.loads(ipr.read())


@pytest.mark.django_db
class TestImporterInterface:
    # def test_save_ip(self, hosting_provider, base_importer):
    #     """
    #     Test saving IPv4 and IPv6 networks to the database
    #     """
    #     testing_ipv4 = "191.233.8.24/29"
    #     testing_ipv6 = "2603:1010:304::140/123"

    #     assert (
    #         GreencheckIp.objects.all().count() == 0
    #     )  # Test: database is empty (for IP)
    #     hosting_provider.save()  # Initialize hosting provider in database

    #     # Import a single IPv4 network
    #     BaseImporter.save_ip(base_importer, testing_ipv4)

    #     assert (
    #         GreencheckIp.objects.all().count() == 1
    #     )  # Test: IPv4 is saved after insertion

    #     # Import a single IPv6 network
    #     BaseImporter.save_ip(base_importer, testing_ipv6)

    #     assert (
    #         GreencheckIp.objects.all().count() == 2
    #     )  # Test: IPv6 is saved after insertion

    # def test_save_asn(self, hosting_provider, base_importer):
    #     """
    #     Test saving Autonomous System Numbers (ASN) networks to the database
    #     """
    #     testing_asn = "AS27407"

    #     assert (
    #         GreencheckASN.objects.all().count() == 0
    #     )  # Test: database is empty (for ASN)
    #     hosting_provider.save()  # Initialize hosting provider in database

    #     # Import a single ASN network
    #     BaseImporter.save_asn(base_importer, testing_asn)

    #     assert (
    #         GreencheckASN.objects.all().count() == 1
    #     )  # Test: ASN is saved after insertion

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

        # TODO: This can be replaced by having a some dummy data imported beforehand
        # ASN dummy database data
        GreencheckASN.objects.bulk_create([
            GreencheckASN(hostingprovider=hosting_provider, asn='29154', active=True),
            GreencheckASN(hostingprovider=hosting_provider, asn='27466', active=False),
            GreencheckASN(hostingprovider=hosting_provider, asn='270119', active=True),
            GreencheckASN(hostingprovider=hosting_provider, asn='27566', active=False),
            GreencheckASN(hostingprovider=hosting_provider, asn='270132', active=True),
            GreencheckASN(hostingprovider=hosting_provider, asn='230132', active=True),
        ])

        # IP dummy database data
        GreencheckIp.objects.bulk_create([
            GreencheckIp(hostingprovider=hosting_provider, active=False, ip_start="40.80.168.113", ip_end="40.80.168.119",),
            GreencheckIp(hostingprovider=hosting_provider, active=False, ip_start="18.208.0.1", ip_end="18.215.255.255",),
            GreencheckIp(hostingprovider=hosting_provider, active=True, ip_start="2603:1040:a06:1::141", ip_end="2603:1040:a06:1::15f",),
            GreencheckIp(hostingprovider=hosting_provider, active=True, ip_start="2603:1020:605::141", ip_end="2603:1020:605::15f",),
            GreencheckIp(hostingprovider=hosting_provider, active=False, ip_start="2603:1020:705:1::141", ip_end="2603:1020:705:1::15f",),
            GreencheckIp(hostingprovider=hosting_provider, active=False, ip_start="43.81.168.113", ip_end="43.81.168.119",),
        ])

        # Process list of addresses in JSON file
        BaseImporter.process_addresses(base_importer, sample_data)

        all_asn = GreencheckASN.objects.all()

        assert (
            GreencheckIp.objects.all().count() == 63
            and GreencheckASN.objects.all().count() == 5
        )  # Test: list of IPv4,IPv6 and ASN is saved after insertion
