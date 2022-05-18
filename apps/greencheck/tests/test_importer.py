import pytest
import pathlib
from io import StringIO

from django.core.management import call_command
from apps.greencheck.management.commands import update_equinix_ip_ranges
from apps.accounts.models import Hostingprovider
from apps.greencheck.models import GreencheckIp, GreencheckASN

from django.conf import settings


@pytest.fixture
def equinix_test_dataset():
    """
    Retrieve a locally saved sample from the population as dataset to use for this test
    Return: list format of the test dataset
    """
    this_file = pathlib.Path(__file__)
    path = this_file.parent.parent.joinpath("fixtures", "equinix_dataset.txt")

    list_of_ips = []
    with open(path) as file:
        for line in file.readlines():
            if line.startswith("AS") or line[0].isdigit():
                list_of_ips.append(line.split(" ", 1)[0])

    return list_of_ips


@pytest.mark.django_db
class TestEquinixImportCommand:
    """
    This just tests that we have a management command that can run.
    We _could_ mock the call to fetch ip ranges, if this turns out to be a slow test.
    """

    def test_handle(self, mocker, equinix_test_dataset):

        # mock the call to `retrieve_dataset`, and return
        # our local text file instead of making a
        # network request. This gives consistent
        # input and output we can check for in our assertions

        # identify the method we want to modify to return a new
        # value for
        path_to_mock = (
            "apps.greencheck.management.commands.importers."
            "equinix_importer.EquinixImporter."
            "fetch_data"
        )

        # define the mock return value to call when
        # the `retrieve_dataset` method is called, instead
        mocker.patch(
            path_to_mock, return_value=equinix_test_dataset,
        )

        out = StringIO()
        call_command("equinix_importer", stdout=out)
        assert "Import Complete:" in out.getvalue()
        assert "21 new IPV4 networks" in out.getvalue()
        assert "13 IPV6 networks" in out.getvalue()
        assert "15 AS Networks" in out.getvalue()
