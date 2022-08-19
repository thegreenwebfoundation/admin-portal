from conftest import csv_file
from io import StringIO
import pathlib


import pytest
from django.core.management import call_command

from apps.greencheck.bulk_importers import (
    ImporterCSV,
    MissingHoster,
    MissingPath,
    EmberCO2Import,
)
from apps.greencheck.models import GreencheckIp
from apps.greencheck.models.checks import CO2Intensity


@pytest.fixture
def sample_country_row():
    return {
        "country_or_region": "Afghanistan",
        "country_code": "AFG",
        "year": "2020",
        "emissions_intensity_gco2_per_kwh": "115.385",
    }


@pytest.fixture
def sample_fossil_share_row():
    return {
        "country_or_region": "Afghanistan",
        "country_code": "AFG",
        "year": "2020",
        "variable": "Fossil",
        "share_of_generation_pct": "15.38",
        "latest_year": "2020",
    }

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


@pytest.fixture
def fossil_csv_path():

    greencheck_app_root = pathlib.Path(__file__).parent.parent

    return (
        greencheck_app_root
        / "fixtures"
        / "ember-2021-share-from-fossil-fuels-sample.csv"
    )


@pytest.mark.django_db
class TestEmberCO2Import:
    def test_return_csv(self, fossil_csv_path):
        """
        Do we get back a list of dicts we can work with easily?
        """
        importer = EmberCO2Import()
        res = importer.parse_csv(fossil_csv_path)

        # do we have a list we can easily manipulate?
        assert isinstance(res, list)
        assert len(res) > 1
        # do we have dicts we can access?
        assert isinstance(res[0], dict)

    def test_load_co2_intensity_data(
        self, sample_country_row, sample_fossil_share_row, fossil_csv_path
    ):

        importer = EmberCO2Import()
        importer.load_fossil_data(fossil_csv_path)

        country, *rest = importer.load_co2_intensity_data([sample_country_row])

        # check the geo info for lookups
        assert country.country_name == sample_country_row["country_or_region"]
        assert country.country_code_iso_3 == sample_country_row["country_code"]
        assert country.country_code_iso_2 == "AF"

        # then check the fossil and carbon intensity numbers we want to expose
        assert (
            country.carbon_intensity
            == sample_country_row["emissions_intensity_gco2_per_kwh"]
        )
        assert country.carbon_intensity_type == "avg"
        assert (
            country.generation_from_fossil
            == sample_fossil_share_row["share_of_generation_pct"]
        )

        # do now have the CO2 Intensity figures for our country in the db?
        assert CO2Intensity.objects.count() == 1

