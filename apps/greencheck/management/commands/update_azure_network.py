from apps.greencheck.importers.azure_importer import AzureImporter
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        importer = AzureImporter()
        data = importer.fetch_data_from_source()
        importer.process_addresses(data)

        # TODO: Implement output
