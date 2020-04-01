import ipaddress
import json
import logging

import requests
from django.core.management.base import BaseCommand
from django.db import connection

from apps.accounts.models import Hostingprovider
from apps.greencheck.bulk_importers import ImporterCSV

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Update IP ranges for the given provider. Expects a hosting provider id, and a path to a csv file"

    def add_arguments(self, parser):
        parser.add_argument("hoster", type=str, help="The id of the hosting provider")
        parser.add_argument("csv-path", type=str, help="Path to the required csv file")

    def handle(self, *args, **options):

        hosting_provider = Hostingprovider.objects.get(pk=options["hoster"])
        path = options["csv-path"]

        importer = ImporterCSV(hosting_provider, path)

        logger.info(f"Adding ip addresses for {hosting_provider}")

        res = importer.run()
        green_ipv4s = res["ipv4"]

        self.stdout.write(
            f"Import Complete: Added {len(green_ipv4s)} new IPV4 addresses for {hosting_provider}"
        )
