import pytest
import pathlib
import ipaddress
import json
from io import StringIO

from django.core.management import call_command

from apps.accounts.models import Hostingprovider
from apps.greencheck.models import GreencheckIp
from apps.greencheck.bulk_importers import ImporterCSV, MissingHoster, MissingPath

@pytest.mark.django_db
class TestImporterCSV:

    @pytest.mark.only
    def test_add_green_ipv4_for_hoster(self, hosting_provider, csv_file):
        # so we have an id we can use when associated new IPs with it
        hosting_provider.save()
        bulk_importer = ImporterCSV(hosting_provider, csv_file)

        assert GreencheckIp.objects.count() == 0

        res = bulk_importer.run()
        green_ips = [gcip.ip_start for gcip in GreencheckIp.objects.all()]

        assert len(res['ipv4']) == 10
        for ip_addy in bulk_importer.ips:
            assert str(ip_addy) in green_ips

    @pytest.mark.only
    def test_needs_a_path_for_the_csv(self, hosting_provider):
        with pytest.raises(Exception):
            assert ImporterCSV(hosting_provider)

    @pytest.mark.only
    def test_needs_a_hosting_provider(self, csv_file):
        with pytest.raises(MissingHoster):
            assert ImporterCSV("2", csv_file)

    @pytest.mark.only
    def test_needs_a_path_for_the_csv(self, hosting_provider):
        with pytest.raises(MissingPath):
            assert ImporterCSV(hosting_provider, None)


    @pytest.mark.only
    def test_needs_a_hosting_provider(self, csv_file):
        with pytest.raises(MissingHoster):
            assert ImporterCSV("2", csv_file)


@pytest.mark.django_db
class TestCSVImportCommand:
    """
    This tests that we have a management command that can run, and checks
    for existence of the necessary command line args.
    """

    @pytest.mark.only
    def test_handle(self, hosting_provider, csv_file):
        out = StringIO()
        hosting_provider.save()
        call_command("import_from_csv", hosting_provider.id, csv_file, stdout=out)
        assert "Import Complete:" in out.getvalue()
