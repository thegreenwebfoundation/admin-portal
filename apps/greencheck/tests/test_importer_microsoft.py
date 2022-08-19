import pytest
import pathlib
import json
from io import StringIO

from django.core.management import call_command
from apps.greencheck.importers.importer_microsoft import MicrosoftImporter

from django.conf import settings


@pytest.fixture
def sample_data_raw():
    """
    Retrieve a locally saved sample of the population to use for this test
    Return: JSON
    """
    this_file = pathlib.Path(__file__)
    json_path = this_file.parent.parent.joinpath("fixtures", "test_dataset_microsoft.json")
    with open(json_path) as ipr:
        return json.loads(ipr.read())

@pytest.fixture
def sample_data_as_list(sample_data_raw):
    """
    Retrieve a locally saved sample of the population to use for this test and parse it to a list
    Return: List
    """
    importer = MicrosoftImporter()
    return importer.parse_to_list(sample_data_raw)

@pytest.mark.django_db
class TestMicrosoftImporter:
    def test_parse_to_list(self, sample_data_raw):
        """
        Test the parsing function.
        """
        # Initialize Microsoft importer
        importer = MicrosoftImporter()

        # Run parse list with sample data
        list_of_addresses = importer.parse_to_list(sample_data_raw)

        # Test: resulting list contains items
        assert len(list_of_addresses) > 0

@pytest.mark.django_db
class TestMicrosoftImportCommand:
    """
    This just tests that we have a management command that can run.
    We _could_ mock the call to fetch ip ranges, if this turns out to be a slow test.
    """

    def test_handle(self, mocker, sample_data_as_list):
        # mock the call to retrieve from source, to a locally stored
        # testing sample. By instead using the test sample,
        # we avoid unnecessary network requests.

        # identify method we want to mock
        path_to_mock = (
            "apps.greencheck.importers.importer_microsoft."
            "MicrosoftImporter.fetch_data_from_source"
        )

        # define a different return when the targeted mock
        # method is called
        mocker.patch(
            path_to_mock, return_value=sample_data_as_list,
        )

        call_command("update_networks_in_db_microsoft")
