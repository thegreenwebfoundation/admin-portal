import csv
import logging

from iso3166 import countries

from apps.greencheck.models.checks import CO2Intensity

logger = logging.getLogger(__name__)


class EmberCO2Import:
    """
    An importer for adding data from the Ember carbon intensity information
    """

    fossil_share_rows = []

    def parse_csv(self, csv_path):
        """
        Parse a CSV file at the provided path, and return a list of
        dicts representing each row.
        """
        # parse CSV and return list of dicts
        with open(csv_path) as csv_file:

            rows = csv.DictReader(csv_file)

            return [row for row in rows]

    def load_fossil_data(self, csv_path):
        """
        Add our list of countries with their share
        of fossil generation
        """
        self.fossil_share_rows = self.parse_csv(csv_path)

    def load_co2_intensity_data(self, avg_co2_rows):
        """
        Take a list of dicts and create a CO2Intensity
        reading for each one.
        """

        created_readings = []

        for row in avg_co2_rows:

            # add a co2 reading, and the kind (avg),
            obj, created = CO2Intensity.objects.get_or_create(
                country_name=row["country_or_region"],
                carbon_intensity=row["emissions_intensity_gco2_per_kwh"],
                year=row["year"],
                country_code_iso_3=row["country_code"],
                carbon_intensity_type="avg",
            )

            # make sure we have both ISO country codes to lookups that
            # use ISO2 codes
            country = countries.get(obj.country_code_iso_3)
            obj.country_code_iso_2 = country.alpha2

            # add fossil generation share
            obj.generation_from_fossil = self.get_fossil_generation_share(obj)

            obj.save()
            created_readings.append(obj)

        return created_readings

    def get_fossil_generation_share(self, obj: CO2Intensity) -> float:
        """
        Accept a CO2Intensity object and return the
        information about the share of energy coming
        from fossil fuels
        """

        matching_fossil_row, *rest = [
            row
            for row in self.fossil_share_rows
            if obj.country_name == row["country_or_region"]
        ]

        return matching_fossil_row.get("share_of_generation_pct")
