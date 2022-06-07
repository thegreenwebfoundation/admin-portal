from apps.greencheck.importers.importer_amazon import AmazonImporter
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        importer = AmazonImporter()
        data = importer.fetch_data_from_source()
        update_message = importer.process_addresses(data)
        
        self.stdout.write(update_message)
