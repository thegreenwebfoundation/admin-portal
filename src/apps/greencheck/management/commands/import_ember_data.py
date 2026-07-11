import logging
from apps.greencheck import bulk_importers

from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import country carbon intensity data from Ember"

    def add_arguments(self, parser):
        parser.add_argument(
            "country_co2_csv_path",
            type=str,
            help="the local path to the csv containing country co2 info",
        )
        parser.add_argument(
            "country_fossil_gen_csv_path",
            type=str,
            help=(
                "the local path to the csv containing info about "
                "the share of fossil fuel generation"
            ),
        )

    def handle(self, *args, **options):
        """Import country CO2 info"""
        importer = bulk_importers.EmberCO2Import()

        country_co2 = importer.parse_csv(options["country_co2_csv_path"])

        importer.load_fossil_data(options["country_fossil_gen_csv_path"])
        added_countries = importer.load_co2_intensity_data(country_co2)

        self.stdout.write(
            f"Import Complete: Added CO2 info for {len(added_countries)} countries."
        )
