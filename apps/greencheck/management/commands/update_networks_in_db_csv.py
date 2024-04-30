import logging

from django.core.management.base import BaseCommand

from apps.accounts.models import Hostingprovider
from apps.greencheck.importers.importer_csv import CSVImporter

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Update IP ranges for the given provider. "
        "Expects a hosting provider id, and a path to a csv file"
    )

    def add_arguments(self, parser):
        parser.add_argument("provider", type=str, help="The id of the hosting provider")
        parser.add_argument("csv-path", type=str, help="Path to the required csv file")

    def handle(self, *args, **options):
        hosting_provider = Hostingprovider.objects.get(pk=options["provider"])
        path = options["csv-path"]

        importer = CSVImporter()
        opened_file = open(path)
        rows = importer.fetch_data_from_source(opened_file)
        list_of_addresses = importer.parse_to_list(rows)

        logger.info(f"Adding ip addresses for {hosting_provider}")
        res = importer.process(hosting_provider, list_of_addresses)

        green_ips = res["green_ips"]
        green_asns = res["green_asns"]
        created_green_ips = res["created_green_ips"]
        created_green_asns = res["created_asns"]

        self.stdout.write(
            (
                f"Import Complete for provider {hosting_provider.name }. "
                f"Added {len(created_green_ips)} green IPs, "
                f"and {len(created_green_asns)} green ASNs. "
                f"Updated {len(green_ips)} green IPs, "
                f"and {len(green_asns)} green ASNs."
            )
        )
