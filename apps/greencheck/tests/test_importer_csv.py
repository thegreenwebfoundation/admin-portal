import pathlib
from io import StringIO

import pytest
from django.conf import settings
from django.core.management import call_command

from apps.accounts.models.hosting import Hostingprovider
from apps.greencheck.importers.importer_csv import CSVImporter


@pytest.fixture
def test_csv_path() -> str:
    csv_path = (
        pathlib.Path(settings.ROOT)
        / "apps"
        / "greencheck"
        / "fixtures"
        / "test_dataset.csv"
    )
    return str(csv_path)


@pytest.mark.django_db
class TestCSVImporter:
    def test_parse_to_list(self, test_csv_path, hosting_provider: Hostingprovider):
        """
        Test the parsing function.
        """
        # Initialize Csv importer
        # hosting_provider.save()
        importer = CSVImporter()

        # Run parse list with sample data
        opened_file = open(test_csv_path)
        rows = importer.fetch_data_from_source(opened_file)
        list_of_addresses = importer.parse_to_list(rows)

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

        expected_single_ip_range = ("104.21.2.197", "104.21.2.199")
        assert expected_ip_range in list_of_addresses
        assert expected_single_ip_range in list_of_addresses

    def test_process_imports(self, test_csv_path, hosting_provider: Hostingprovider):
        hosting_provider.save()
        importer = CSVImporter()

        # Run parse list with sample data
        opened_file = open(test_csv_path)
        rows = importer.fetch_data_from_source(opened_file)
        list_of_addresses = importer.parse_to_list(rows)
        created_networks = importer.process(
            provider=hosting_provider, list_of_networks=list_of_addresses
        )

        # we should have seen one AS network added
        created_green_ips = created_networks["created_green_ips"]
        created_green_asns = created_networks["created_asns"]

        assert len(created_green_ips) == 3
        assert len(created_green_asns) == 1

        # have we created the new Green ASN in the db?
        green_asns = hosting_provider.greencheckasn_set.all()

        for green_asn in created_green_asns:
            assert green_asn in green_asns

        # have we created the green ip ranges in the db?
        green_ips = hosting_provider.greencheckip_set.all().order_by("ip_start")

        for green_ip in created_green_ips:
            assert green_ip in green_ips

    def test_preview_imports(self, test_csv_path, hosting_provider: Hostingprovider):
        """
        Can we see a representation of the data we would import before
        we run the import it?
        """
        # Initialize Csv importer
        hosting_provider.save()
        importer = CSVImporter()

        # Run parse list with sample data
        opened_file = open(test_csv_path)
        rows = importer.fetch_data_from_source(opened_file)
        list_of_addresses = importer.parse_to_list(rows)

        preview = importer.preview(
            provider=hosting_provider, list_of_networks=list_of_addresses
        )

        assert len(preview["green_ips"]) == 3
        assert len(preview["green_asns"]) == 1

    def test_view_processed_imports(
        self, test_csv_path, hosting_provider: Hostingprovider
    ):
        """
        Can we compare the state of an import to the networks already in the database
        for this provider?
        """
        # Initialize Csv importer
        hosting_provider.save()
        importer = CSVImporter()
        opened_file = open(test_csv_path)
        rows = importer.fetch_data_from_source(opened_file)
        list_of_addresses = importer.parse_to_list(rows)
        # Run our import to save them to the database, simulating saving
        # via our the form
        importer.process(provider=hosting_provider, list_of_networks=list_of_addresses)

        # Generate a view of the data, to check if we are fetching from
        # the database now
        preview = importer.preview(
            provider=hosting_provider, list_of_networks=list_of_addresses
        )

        green_ips = [green_ip for green_ip in preview["green_ips"]]
        green_asns = [green_asn for green_asn in preview["green_asns"]]

        # are these the IPs checked against the database?
        for green_ip in green_ips:
            assert green_ip.id is not None

        # are these the ASNs checked against the database?
        for green_asn in green_asns:
            assert green_asn.id is not None


@pytest.mark.django_db
class TestCSVImportCommand:
    """
    This tests that we have a management command that can run, and checks
    for existence of the necessary command line args.
    """

    def test_handle(self, hosting_provider, test_csv_path):
        out = StringIO()
        hosting_provider.save()
        call_command(
            "update_networks_in_db_csv", hosting_provider.id, test_csv_path, stdout=out
        )
        assert "Import Complete" in out.getvalue()

    def test_handle_running_twice(self, hosting_provider, test_csv_path):
        first_output = StringIO()
        second_output = StringIO()
        hosting_provider.save()

        call_command(
            "update_networks_in_db_csv",
            hosting_provider.id,
            test_csv_path,
            stdout=first_output,
        )
        call_command(
            "update_networks_in_db_csv",
            hosting_provider.id,
            test_csv_path,
            stdout=second_output,
        )
        assert "Import Complete" in first_output.getvalue()
        assert "Import Complete" in second_output.getvalue()
