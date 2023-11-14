import pytest
import pathlib
import json

from apps.greencheck.importers import NetworkImporter
from apps.greencheck.models import GreencheckIp, GreencheckASN


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
class TestNetworkImporter:
    def test_save_ip(self, hosting_provider_factory):
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
        provider = hosting_provider_factory.create()
        importer = NetworkImporter(provider)

        assert GreencheckIp.objects.all().count() == 0

        # Import a single IPv4 network
        importer.save_ip(testing_ipv4_range)

        assert (
            GreencheckIp.objects.all().count() == 1
        )  # Test: database is empty (for IP)

        # Import a single IPv4 network
        importer.save_ip(testing_ipv6_range)

        assert (
            GreencheckIp.objects.all().count() == 2
        )  # Test: database is empty (for IP)

        # # Import a single IPv4 network
        # importer.save_ip(testing_ipv4_network)

        # assert (
        #     GreencheckIp.objects.all().count() == 3
        # )  # Test: IPv4 is saved after insertion

        # # Import a single IPv6 network
        # base_importer.save_ip(testing_ipv6_network)

        # assert (
        #     GreencheckIp.objects.all().count() == 4
        # )  # Test: IPv6 is saved after insertion

    # @pytest.mark.skip(reason="WIP")
    def test_save_asn(self, hosting_provider_factory):
        """
        Test saving Autonomous System Numbers (ASN) networks to the database
        """
        testing_asn = "AS27407"
        provider = hosting_provider_factory.create()
        importer = NetworkImporter(provider)

        assert (
            GreencheckASN.objects.all().count() == 0
        )  # Test: database is empty (for ASN)

        # Import a single ASN network
        importer.save_asn(testing_asn)

        assert (
            GreencheckASN.objects.all().count() == 1
        )  # Test: ASN is saved after insertion

    def test_process_addresses(self, hosting_provider_factory, sample_data):
        """
        Test processing addresses(IPv4, IPv6 and/or ASN) to save
        a list with various types of networks
        """

        provider = hosting_provider_factory.create()
        importer = NetworkImporter(provider)

        # Process list of addresses in JSON file
        importer.process_addresses(sample_data)

        # Test: list of IPv4,IPv6 and ASN is saved after insertion
        assert (
            GreencheckIp.objects.all().count() == 63
            and GreencheckASN.objects.all().count() == 5
        )
