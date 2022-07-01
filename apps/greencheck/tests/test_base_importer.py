import ipaddress
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
    def test_update_asn_create(self, hosting_provider, base_importer):
        """
        Test creating Autonomous System Numbers (ASN) networks to the database
        """
        hosting_provider.save()  # Initialize hosting provider in database
        asn_testing_data = ["AS27407", "AS27403", "AS27405"]
        asn_count = GreencheckASN.objects.all().count()

        # Import a list of ASN networks
        BaseImporter.update_asn(base_importer, asn_testing_data)

        assert GreencheckASN.objects.all().count() == asn_count + len(
            asn_testing_data
        )  # Test: ASN values are saved after insertion

    def test_update_asn_activate_entry(self, hosting_provider, base_importer):
        """
        Test activating a inactive ASN network
        """
        hosting_provider.save()  # Initialize hosting provider in database
        asn_number = 27407
        existing_asn = "AS" + str(asn_number)

        GreencheckASN.objects.create(
            hostingprovider=hosting_provider,
            active=False,
            asn=asn_number,
        )
        assert (
            GreencheckASN.objects.all().count() == 1
        )  # Test: Check that there is only one entry added to the database
        assert (
            GreencheckASN.objects.first().active == False
        )  # Test: Check that this entry is inactive

        # Import existing ASN network again
        BaseImporter.update_asn(base_importer, [(existing_asn)])
        assert (
            GreencheckASN.objects.first().active == True
        )  # Test: Check that this entry is activated now

    def test_update_asn_double_insert(self, hosting_provider, base_importer):
        """
        Test updating ASN networks twice through the update function
        """
        hosting_provider.save()  # Initialize hosting provider in database
        asn_count = GreencheckASN.objects.all().count()

        assert asn_count == 0  # Database is empty
        asn_testing_data = ["AS27407"]

        # Import a list of new ASN networks
        BaseImporter.update_asn(base_importer, asn_testing_data)

        assert GreencheckASN.objects.all().count() == asn_count + len(
            asn_testing_data
        )  # Test: ASN values are saved after insertion

        # Since the ASN list is inserted, we can try to update
        # these values again
        BaseImporter.update_asn(base_importer, asn_testing_data)

        assert GreencheckASN.objects.all().count() == asn_count + len(
            asn_testing_data
        )  # Test: ASN values are updated and no new entry is saved

    def test_update_asn_existing_entries(self, hosting_provider, base_importer):
        """
        Test updating already existing ASN networks
        """
        hosting_provider.save()  # Initialize hosting provider in database
        asn_number = 27407
        existing_asn = "AS" + str(asn_number)

        GreencheckASN.objects.create(
            hostingprovider=hosting_provider,
            active=True,
            asn=asn_number,
        )
        asn_count = GreencheckASN.objects.all().count()
        assert asn_count == 1  # Test: Database already has an entry

        # Import existing ASN network again
        BaseImporter.update_asn(base_importer, [(existing_asn)])

        assert (
            GreencheckASN.objects.all().count() == asn_count
        )  # Test: ASN value is updated and no new entry is saved

    def test_update_ip_create(self, hosting_provider, base_importer):
        """
        Test creating IPv4 and IPv6 networks to the database
        """
        hosting_provider.save()  # Initialize hosting provider in database
        ip_testing_data = [
            "191.233.8.24/29",
            "191.105.2.24/29",
            "2603:1010:304::140/123",
            "2253:1310:222::140/123",
        ]
        ip_count = GreencheckIp.objects.all().count()

        # Import a list of IP networks
        BaseImporter.update_ip(base_importer, ip_testing_data)

        assert GreencheckIp.objects.all().count() == ip_count + len(
            ip_testing_data
        )  # Test: IPv4 and IPv6 ip addresses are saved after insertion

    def test_update_ip_activate_entry(self, hosting_provider, base_importer):
        """
        Test activating an inactive IP network
        """
        hosting_provider.save()  # Initialize hosting provider in database
        existing_network = "191.105.2.24/29"
        network = ipaddress.ip_network(existing_network)
        existing_start_ip = str(network[1])
        existing_end_ip = str(network[-1])

        GreencheckIp.objects.create(
            hostingprovider=hosting_provider,
            active=False,
            ip_start=existing_start_ip,
            ip_end=existing_end_ip,
        )
        assert (
            GreencheckIp.objects.all().count() == 1
        )  # Test: Check that there is only one entry added to the database
        assert (
            GreencheckIp.objects.first().active == False
        )  # Test: Check that this entry is inactive

        # Import existing IP network again
        BaseImporter.update_ip(base_importer, [(existing_network)])
        assert (
            GreencheckIp.objects.first().active == True
        )  # Test: Check that this entry is activated now

    def test_update_ip_double_insert(self, hosting_provider, base_importer):
        """
        Test updating IPv4 and IPv6 networks twice through the update function
        """
        hosting_provider.save()  # Initialize hosting provider in database
        ip_testing_data = ["191.105.2.24/29", "2603:1010:304::140/123"]

        ip_count = GreencheckIp.objects.all().count()
        assert ip_count == 0  # Test: Database is empty

        # Import a list of new IP networks
        BaseImporter.update_ip(base_importer, ip_testing_data)

        assert GreencheckIp.objects.all().count() == ip_count + len(
            ip_testing_data
        )  # Test: IP values are saved after insertion

        # Since the IP list is inserted, we can try to update
        # these values again
        BaseImporter.update_ip(base_importer, ip_testing_data)

        assert GreencheckIp.objects.all().count() == ip_count + len(
            ip_testing_data
        )  # Test: IP values are updated and no new entry is saved

    def test_update_ip_existing_entries(self, hosting_provider, base_importer):
        """
        Test updating already existing IPv4 and IPv6 networks
        """
        hosting_provider.save()  # Initialize hosting provider in database

        existing_network = "191.105.2.24/29"
        network = ipaddress.ip_network(existing_network)
        existing_start_ip = str(network[1])
        existing_end_ip = str(network[-1])

        GreencheckIp.objects.create(
            hostingprovider=hosting_provider,
            active=True,
            ip_start=existing_start_ip,
            ip_end=existing_end_ip,
        )
        ip_count = GreencheckIp.objects.all().count()
        assert ip_count == 1  # Database already has an entry

        # Import existing IP network again
        BaseImporter.update_ip(base_importer, [(existing_network)])

        assert (
            GreencheckIp.objects.all().count() == ip_count
        )  # Test: IP value is updated and no new entry is saved

    def test_process_addresses(self, hosting_provider, base_importer, sample_data):
        """
        Test processing addresses(IPv4, IPv6 and/or ASN) to save
        a list with various types of networks
        """
        hosting_provider.save()  # Initialize hosting provider in database
        assert (
            GreencheckIp.objects.all().count() == 0
        )  # Test: database is empty (for IP)
        assert (
            GreencheckASN.objects.all().count() == 0
        )  # Test: database is empty (for ASN)

        # Insert ASN dummy data
        GreencheckASN.objects.bulk_create(
            [
                # Next records already exist
                GreencheckASN(
                    hostingprovider=hosting_provider, asn="29154", active=True
                ),
                GreencheckASN(
                    hostingprovider=hosting_provider, asn="27466", active=False
                ),
                GreencheckASN(
                    hostingprovider=hosting_provider, asn="270119", active=True
                ),
                GreencheckASN(
                    hostingprovider=hosting_provider, asn="27566", active=False
                ),
            ]
        )

        # Insert IP dummy data
        GreencheckIp.objects.bulk_create(
            [
                # Next records already exist
                GreencheckIp(
                    hostingprovider=hosting_provider,
                    active=False,
                    ip_start="40.80.168.113",
                    ip_end="40.80.168.119",
                ),
                GreencheckIp(
                    hostingprovider=hosting_provider,
                    active=False,
                    ip_start="18.208.0.1",
                    ip_end="18.215.255.255",
                ),
                GreencheckIp(
                    hostingprovider=hosting_provider,
                    active=True,
                    ip_start="2603:1040:a06:1::141",
                    ip_end="2603:1040:a06:1::15f",
                ),
                GreencheckIp(
                    hostingprovider=hosting_provider,
                    active=True,
                    ip_start="2603:1020:605::141",
                    ip_end="2603:1020:605::15f",
                ),
                GreencheckIp(
                    hostingprovider=hosting_provider,
                    active=False,
                    ip_start="2603:1020:705:1::141",
                    ip_end="2603:1020:705:1::15f",
                ),
            ]
        )

        # Process list of addresses in JSON file
        BaseImporter.process_addresses(base_importer, sample_data)

        assert (
            GreencheckIp.objects.all().count() == 63
            and GreencheckASN.objects.all().count() == 5
        )  # Test: list of IPv4, IPv6 and ASN is saved after insertion
