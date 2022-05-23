from apps.greencheck.importers.aws_importer import AwsImporter
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        importer = AwsImporter()
        data = importer.fetch_data_from_source()
        importer.process_addresses(data)

        # TODO: Implement output
