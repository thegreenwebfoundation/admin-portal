from conftest import csv_file
from io import StringIO

import pytest
from django.core.management import call_command

from apps.greencheck.bulk_importers import ImporterCSV, MissingHoster, MissingPath
from apps.greencheck.models import GreencheckIp

file_string = """IP
139.162.130.199
139.162.166.185
172.104.145.244
139.162.156.10"""


@pytest.mark.django_db
class TestImporterCSV:
    def test_add_green_ipv4_for_hoster(self, hosting_provider):
        # so we have an id we can use when associating new IPs with the hoster
        hosting_provider.save()

        bulk_importer = ImporterCSV(hosting_provider)

        assert GreencheckIp.objects.count() == 0

        bulk_importer.ips_from_file(StringIO(file_string))
        res = bulk_importer.run()
        green_ips = [gcip.ip_start for gcip in GreencheckIp.objects.all()]

        assert len(res["ipv4"]["created"]) == 4
        for ip_addy in bulk_importer.ips:
            assert str(ip_addy) in green_ips

    def test_needs_a_path_for_the_csv(self, hosting_provider):
        with pytest.raises(MissingPath):
            importer = ImporterCSV(hosting_provider)
            importer.ips_from_path(None)

    def test_needs_a_hosting_provider(self):
        with pytest.raises(MissingHoster):
            assert ImporterCSV(None)


@pytest.mark.django_db
class TestCSVImportCommand:
    """
    This tests that we have a management command that can run, and checks
    for existence of the necessary command line args.
    """

    def test_handle(self, hosting_provider, csv_file):
        out = StringIO()
        hosting_provider.save()
        call_command("import_from_csv", hosting_provider.id, csv_file, stdout=out)
        assert "Import Complete:" in out.getvalue()
