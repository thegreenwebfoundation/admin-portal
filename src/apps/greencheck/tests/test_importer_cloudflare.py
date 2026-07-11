import pytest
import pathlib
import json

from django.core.management import call_command
from apps.greencheck.importers import CloudflareImporter
from ..importers.network_importer import is_ip_network



@pytest.fixture
def sample_data_ipv4() -> str:
    this_file = pathlib.Path(__file__)
    file_path = this_file.parent.parent.joinpath("fixtures", "test_dataset_cloudflare.ipv4.txt")
    
    with open(file_path) as ipv4s:
        return ipv4s.read()

@pytest.fixture
def sample_data_ipv6() -> str:
    this_file = pathlib.Path(__file__)
    file_path = this_file.parent.parent.joinpath("fixtures", "test_dataset_cloudflare.ipv6.txt")
    with open(file_path) as ipv6s:
        return ipv6s.read()

@pytest.fixture
def sample_data_raw(sample_data_ipv6, sample_data_ipv4) -> list[str]:
    """
    return the same values as as returned by the fetch_data_from_source method
    """
    return *sample_data_ipv6.splitlines(), *sample_data_ipv4.splitlines()



@pytest.fixture()
def settings_with_cloudflare_provider(settings):
    settings.CLOUDFLARE_PROVIDER_ID = 123
    return settings

class TestCloudflareImporter:

    def test_parse_to_list(self, settings_with_cloudflare_provider, hosting_provider_factory, sample_data_raw):
        """
        Test the parsing function converts the json into a consisten list our
        importer can process
        """

        # Given: an initialised importer
        importer = CloudflareImporter()

        # When: I parse the published info
        list_of_addresses = importer.parse_to_list(sample_data_raw)

        # Then: I should see a list of IP and IPv6 addresses
        for network in list_of_addresses:
            assert is_ip_network(network)

    @pytest.mark.django_db
    def test_process_ip_import(
        self,
        settings_with_cloudflare_provider,
        hosting_provider_factory,
        sample_data_raw,
    ):
        """
        Test that we can import the parsed and reshaped list of IP addresses.
        """

        # Given: a provider standing in for our Cloudflare
        fake_cf = hosting_provider_factory.create(
            id=settings_with_cloudflare_provider.CLOUDFLARE_PROVIDER_ID
        )
        # And: an initialised importer
        importer = CloudflareImporter()

        # When: parse the published info, and process the import
        list_of_addresses = importer.parse_to_list(sample_data_raw)
        import_result = importer.process(list_of_addresses)

        assert fake_cf.greencheckip_set.all().count() == len(
            import_result["created_green_ips"]
        )

    @pytest.mark.django_db
    def test_process_repeat_ip_import(
        self, settings_with_cloudflare_provider, hosting_provider_factory, sample_data_raw
    ):
        """
        Test that a second import does not duplicate ip addresses.
        """

        # Given: a provider standing in for our Cloudflare
        fake_cf = hosting_provider_factory.create(
            id=settings_with_cloudflare_provider.CLOUDFLARE_PROVIDER_ID
        )
        # And: an initialised importer
        importer = CloudflareImporter()

        # When: parse the published info, and process the import
        list_of_addresses = importer.parse_to_list(sample_data_raw)

        import_result = importer.process(list_of_addresses)

        # And: we have
        repeat_import_result = importer.process(list_of_addresses)

        assert fake_cf.greencheckip_set.all().count() == len(
            import_result["created_green_ips"]
        )

        assert len(repeat_import_result["created_green_ips"]) == 0

        deduped_green_ips = set(repeat_import_result["green_ips"])
        assert fake_cf.greencheckip_set.all().count() == len(deduped_green_ips)


@pytest.mark.django_db
class TestCloudflareImportCommand:
    """
    Test the management command to update the Cloudflare IP ranges
    """

    def test_handle(
        self,
        mocker,
        hosting_provider_factory,
        settings_with_cloudflare_provider,
        sample_data_raw,
    ):
        # mock the call to retrieve from source, to a locally stored
        # testing sample. By instead using the test sample,
        # we avoid unnecessary network requests.

        # identify method we want to mock
        path_to_mock = (
            "apps.greencheck.importers.importer_cloudflare."
            "CloudflareImporter.fetch_data_from_source"
        )
        # Given: a provider standing in for our Cloudflare
        fake_cf = hosting_provider_factory.create(
            id=settings_with_cloudflare_provider.CLOUDFLARE_PROVIDER_ID
        )

        # define a different return when the targeted mock
        # method is called
        mocker.patch(
            path_to_mock,
            return_value=sample_data_raw,
        )

        # When: I run the management command to update the cloudflare ip ranges
        call_command("update_networks_in_db_cloudflare")

        # Then: I should see the ip ranges in the database
        assert fake_cf.greencheckip_set.all().count() == 22
