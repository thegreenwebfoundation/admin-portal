import pytest
import pathlib
import json

from django.core.management import call_command
from apps.greencheck.importers.importer_amazon import AmazonImporter
from ..importers.network_importer import is_ip_network


@pytest.fixture
def sample_data_raw():
    """
    Retrieve a locally saved sample of the population to use for this test
    Return: JSON
    """
    this_file = pathlib.Path(__file__)
    json_path = this_file.parent.parent.joinpath("fixtures", "test_dataset_amazon.json")
    with open(json_path) as ipr:
        return json.loads(ipr.read())


@pytest.fixture()
def settings_with_aws_provider(settings):
    settings.AMAZON_PROVIDER_ID = 123


class TestAmazonImporter:
    def test_parse_to_list(self, settings, hosting_provider_factory, sample_data_raw):
        """
        Test the parsing function converts the json into a consisten list our
        importer can process
        """

        # Given: a provider standing in for our Amazon

        # And: an initialised importer
        importer = AmazonImporter()

        # When: I parse the published info
        list_of_addresses = importer.parse_to_list(sample_data_raw)

        # Then: I should see a list of IP and IPv6 addresses
        for network in list_of_addresses:
            assert is_ip_network(network)

    @pytest.mark.django_db
    def test_process_ip_import(
        self, settings_with_aws_provider, hosting_provider_factory, sample_data_raw
    ):
        """
        Test that we can import the parsed and reshaped list of IP addresses.
        """

        # Given: a provider standing in for our Amazon
        fake_aws = hosting_provider_factory.create(
            id=settings_with_aws_provider.AMAZON_PROVIDER_ID
        )
        # And: an initialised importer
        importer = AmazonImporter()

        # When: parse the published info, and process the import
        list_of_addresses = importer.parse_to_list(sample_data_raw)
        import_result = importer.process(list_of_addresses)

        assert fake_aws.greencheckip_set.all().count() == len(
            import_result["created_green_ips"]
        )

    @pytest.mark.django_db
    def test_process_repeat_ip_import(
        self, settings_with_aws_provider, hosting_provider_factory, sample_data_raw
    ):
        """
        Test that a second import does not duplicate ip addresses.
        """

        # Given: a provider standing in for our Amazon
        fake_aws = hosting_provider_factory.create(
            id=settings_with_aws_provider.AMAZON_PROVIDER_ID
        )
        # And: an initialised importer
        importer = AmazonImporter()

        # When: parse the published info, and process the import
        list_of_addresses = importer.parse_to_list(sample_data_raw)

        import_result = importer.process(list_of_addresses)

        # And: we have
        repeat_import_result = importer.process(list_of_addresses)

        assert fake_aws.greencheckip_set.all().count() == len(
            import_result["created_green_ips"]
        )

        assert len(repeat_import_result["created_green_ips"]) == 0

        deduped_green_ips = set(repeat_import_result["green_ips"])
        assert fake_aws.greencheckip_set.all().count() == len(deduped_green_ips)


@pytest.mark.django_db
class TestAmazonImportCommand:
    """
    This just tests that we have a management command that can run.
    We _could_ mock the call to fetch ip ranges, if this turns out to be a slow test.
    """

    def test_handle(
        self,
        mocker,
        hosting_provider_factory,
        settings_with_aws_provider,
        sample_data_raw,
    ):
        # mock the call to retrieve from source, to a locally stored
        # testing sample. By instead using the test sample,
        # we avoid unnecessary network requests.

        # identify method we want to mock
        path_to_mock = (
            "apps.greencheck.importers.importer_amazon."
            "AmazonImporter.fetch_data_from_source"
        )
        # Given: a provider standing in for our Amazon
        fake_aws = hosting_provider_factory.create(
            id=settings_with_aws_provider.AMAZON_PROVIDER_ID
        )

        # define a different return when the targeted mock
        # method is called
        mocker.patch(
            path_to_mock,
            return_value=sample_data_raw,
        )

        call_command("update_networks_in_db_amazon")

        assert fake_aws.greencheckip_set.all().count() > 0
