import pytest
import pathlib
import json

from apps.greencheck.importers.importer_google import GoogleImporter


@pytest.fixture
def sample_data_raw():
    """
    Retrieve a locally saved sample of the population to use for this test
    Return: JSON
    """
    this_file = pathlib.Path(__file__)
    json_path = this_file.parent.parent.joinpath("fixtures", "test_dataset_google.json")
    with open(json_path) as ipr:
        return json.loads(ipr.read())


@pytest.fixture()
def settings_with_ms_provider(settings):
    settings.GOOGLE_PROVIDER_ID = 123
    return settings


@pytest.mark.django_db
class TestGoogleImporter:
    def test_parse_to_list(self, sample_data_raw):
        """
        Test the parsing function.
        """
        # Initialize Microsoft importer
        importer = GoogleImporter()

        # Run parse list with sample data
        list_of_addresses = importer.parse_to_list(sample_data_raw)

        # Test: resulting list contains items
        assert len(list_of_addresses) > 0
