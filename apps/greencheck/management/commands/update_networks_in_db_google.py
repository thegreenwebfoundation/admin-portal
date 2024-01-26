import logging

from django.core.management.base import BaseCommand

from apps.greencheck.importers.importer_google import GoogleImporter

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Update IP ranges for cloud providers that publish them"

    def handle(self, *args, **options):
        importer = GoogleImporter()
        data = importer.fetch_data_from_source()
        parsed_data = importer.parse_to_list(data)
        result = importer.process(parsed_data)

        update_message = (
            f"Processing complete. Created {len(result['created_asns'])} ASNs,"
            f"and {len(result['created_green_ips'])} IP ranges. "
            f"Updated {len(result['green_asns'])} ASNs, "
            f"and {len(result['green_ips'])} IP ranges. (either IPv4 and/or IPv6)"
        )
        self.stdout.write(update_message)
