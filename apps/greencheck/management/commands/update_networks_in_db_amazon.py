from apps.greencheck.importers.importer_amazon import AmazonImporter
from ...exceptions import ImportingForArchivedProvider
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        importer = AmazonImporter()
        data = importer.fetch_data_from_source()
        parsed_data = importer.parse_to_list(data)

        try:
            result = importer.process(parsed_data)
        except ImportingForArchivedProvider:
            self.stdout.write(
                "The provider is archived. Skipping any further changes to this provider"
            )
            return None

        update_message = (
            f"Processing complete. Created {len(result['created_asns'])} ASNs,"
            f"and {len(result['created_green_ips'])} IP ranges. "
            f"Updated {len(result['green_asns'])} ASNs, "
            f"and {len(result['green_ips'])} IP ranges. (either IPv4 and/or IPv6)"
        )

        self.stdout.write(update_message)
