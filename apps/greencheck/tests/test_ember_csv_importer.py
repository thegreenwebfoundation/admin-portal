import pathlib

import pytest

from apps.greencheck.bulk_importers import (
    EmberCO2Import,
)
from apps.greencheck.models.co2_intensity import CO2Intensity


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
