import pytest
import pathlib

from django.core.management import call_command
from apps.greencheck.importers.importer_equinix import EquinixImporter


@pytest.fixture
def sample_data_raw():
    """
    Retrieve a locally saved sample from the population as dataset to use for this test
    Return: str (contents of the text file)
    """
    this_file = pathlib.Path(__file__)
    path = this_file.parent.parent.joinpath("fixtures", "test_dataset_equinix.txt")

    return open(path).read()


@pytest.mark.django_db
class TestEquinixImporter:
    def test_parse_to_list(self, hosting_provider, sample_data_raw):
        """
        Test the parsing function.
        """
        # Initialize Equinix importer
        importer = EquinixImporter()

        # Run parse list with sample data
        list_of_addresses = importer.parse_to_list(sample_data_raw)

        # Test: resulting list contains items
        assert len(list_of_addresses) > 0


@pytest.mark.django_db
class TestEquinixImportCommand:
    """
    This just tests that we have a management command that can run.
    We _could_ mock the call to fetch ip ranges, if this turns out to be a slow test.
    """

    def test_handle(self, mocker, hosting_provider_factory, settings, sample_data_raw):
        # mock the call to retrieve from source, to a locally stored
        # testing sample. By instead using the test sample,
        # we avoid unnecessary network requests.

        # identify method we want to mock
        path_to_mock = (
            "apps.greencheck.importers.importer_equinix."
            "EquinixImporter.fetch_data_from_source"
        )
        fake_equinix = hosting_provider_factory.create(id=settings.EQUINIX_PROVIDER_ID)

        # define a different return when the targeted mock
        # method is called
        mocker.patch(
            path_to_mock,
            return_value=sample_data_raw,
        )

        call_command("update_networks_in_db_equinix")

        # based on the test data
        assert fake_equinix.greencheckip_set.all().count() == 34
        assert fake_equinix.greencheckasn_set.all().count() == 15
