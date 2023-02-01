import logging
from apps.greencheck import object_storage

from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch a file from object storage for the given bucket and path"

    def add_arguments(self, parser):
        parser.add_argument(
            "bucket",
            type=str,
            help="the name of the bucket to look in",
        )
        parser.add_argument(
            "source_path",
            type=str,
            help=("the path to the file in object storage to fetch"),
        )
        parser.add_argument(
            "destination_path",
            type=str,
            help=("the path save the file to locally"),
        )

    def handle(self, *args, **options):
        """Fetch the file from the bucket, and save locally"""

        bucket_name = options.get('bucket')
        file_path = options.get('source_path')
        dest_path = options.get('destination_path')
        
        self.stdout.write(f"Fetching {file_path} from bucket {bucket_name}, saving to {dest_path}")
        bucket = object_storage.object_storage_bucket(bucket_name)
        
        bucket.download_file(file_path, dest_path)
        
        self.stdout.write(
            f"Done! Your file should be at {dest_path}"
        )
