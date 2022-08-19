from apps.greencheck.importers.importer_microsoft import MicrosoftImporter
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        importer = MicrosoftImporter()
        data = importer.fetch_data_from_source()
        update_message = importer.process_addresses(data)
        
        self.stdout.write(update_message)
        
