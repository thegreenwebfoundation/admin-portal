import pytest
import pathlib
import re
import pandas as pd
from io import StringIO

from django.core.management import call_command
from apps.accounts.models.hosting import Hostingprovider
from apps.greencheck.importers.importer_csv import CSVImporter

from django.conf import settings


@pytest.fixture
def sample_data_raw():
    """
    Retrieve a locally saved sample of the population to use for this test
    Return: CSV
    """
    csv_path = pathlib.Path(settings.ROOT) / "apps" / "greencheck" / "fixtures" / "test_dataset_csv.csv"
    return pd.read_csv(csv_path, header=None)


@pytest.fixture
def sample_data_as_list(sample_data_raw, hosting_provider: Hostingprovider):
    """
    Retrieve a locally saved sample of the population to use for this test and parse it to a list
    Return: List
    """
    importer = CSVImporter()
    return importer.parse_to_list(sample_data_raw)


@pytest.mark.django_db
class TestCSVImporter:
    def test_parse_to_list(self, sample_data_raw, hosting_provider: Hostingprovider):
        """
        Test the parsing function.
        """
        # Initialize Csv importer
        hosting_provider.save()
        importer = CSVImporter(hosting_provider)

        # Run parse list with sample data
        list_of_addresses = importer.parse_to_list(sample_data_raw)

        # Test: resulting list contains some items
        assert len(list_of_addresses) > 0

        # do we have an ip network?
        assert "104.21.2.0/24" in list_of_addresses

        # have we filtered out our incorrect IP network?
        assert "104.21.2.192/24" not in list_of_addresses

        # do we have our expected AS number?
        assert "AS234" in list_of_addresses

        # have we filtered out our bad AS line?
        assert "AS" not in list_of_addresses

        # do we have an IP range in our list
        expected_ip_range = ("104.21.2.197", "104.21.2.199")
        assert expected_ip_range in list_of_addresses

    def test_process_imports(self, sample_data_raw, hosting_provider: Hostingprovider):

        # Initialize Csv importer
        hosting_provider.save()
        importer = CSVImporter(hosting_provider)

        # Run parse list with sample data
        list_of_addresses = importer.parse_to_list(sample_data_raw)
        created_networks = importer.process_addresses(list_of_addresses)
        
        # we should have seen one AS network added
        assert "1 ASN" in created_networks
        # have we created two new IP ranges?
        assert "2 IP" in created_networks
        
        # have we created the new Green ASN in the db?
        green_asns = hosting_provider.greencheckasn_set.all()
        assert green_asns .first().asn == 234

        # have we created the green ip ranges in the db?
        green_ips = hosting_provider.greencheckip_set.all().order_by('ip_start')
        
        # have we converted a network to a range?
        assert green_ips[0].ip_start == "104.21.2.1"
        assert green_ips[0].ip_end == "104.21.2.255"
        
        # have do we have the range added as well?
        assert green_ips[1].ip_start == "104.21.2.197"
        assert green_ips[1].ip_end == "104.21.2.199"
        
    def test_preview_imports(self, sample_data_raw, hosting_provider: Hostingprovider):
        """
        Can we see a representation of the data we would import before
        we run the import it?
        """
        # Initialize Csv importer
        hosting_provider.save()
        importer = CSVImporter(hosting_provider)

        # Run parse list with sample data
        list_of_addresses = importer.parse_to_list(sample_data_raw)
        preview = importer.preview(hosting_provider, list_of_addresses)

        assert len(preview["green_ips"]) == 2
        assert len(preview["green_asns"]) == 1

    def test_view_processed_imports(self, sample_data_raw, hosting_provider: Hostingprovider):
        """
        Can we compare the state of an import to the networks already in the database
        for this provider?
        """
        # Initialize Csv importer
        hosting_provider.save()
        importer = CSVImporter(hosting_provider)

        # Run parse list with sample data
        list_of_addresses = importer.parse_to_list(sample_data_raw)
        # Run our import to save them to the database, simulating saving 
        # via our the form
        created_networks = importer.process_addresses(list_of_addresses)
        # Generate a view of the data, to check if we are fetching from 
        # the database now
        preview = importer.preview(hosting_provider, list_of_addresses)
        
        green_ips = [gip for gip in preview['green_ips']]
        green_asns = [gip for gip in preview['green_asns']]
        
        # are these the IPs checked against the database?
        for green_ip in green_ips:
            assert green_ip.id is not None
            
        # are these the ASNs checked against the database?
        for green_asn in green_asns:
            assert green_asn.id is not None


# @pytest.mark.django_db
# class TestCsvImportCommand:
#     """
#     This just tests that we have a management command that can run.
#     """

#     def test_handle(self, mocker, sample_data_as_list):
#         # mock the call to retrieve from source, to a locally stored
#         # testing sample. By instead using the test sample,
#         # we avoid unnecessary network requests.

#         # identify method we want to mock
#         path_to_mock = (
#             "apps.greencheck.importers.importer_csv."
#             "CSVImporter.fetch_data_from_source"
#         )

#         # define a different return when the targeted mock
#         # method is called
#         mocker.patch(
#             path_to_mock,
#             return_value=sample_data_as_list,
#         )

#         # TODO: Do we need this call command?
#         # call_command("update_networks_in_db_csv")
