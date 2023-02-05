import logging
from apps.greencheck import object_storage

from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch a file from object storage for the given bucket and path"

    def add_arguments(self, parser):
        parser.add_argument(
            "operation",
            type=str,
            help="the type of operation. Either 'get' or 'put'",
        )
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

        operation = options.get('operation')
        bucket_name = options.get('bucket')
        source_path = options.get('source_path')
        dest_path = options.get('destination_path')
        
        bucket = object_storage.object_storage_bucket(bucket_name)

        import ipdb; ipdb.set_trace()
        if operation.lower() not in ("get", "put"):
            raise Exception("Please use one of either 'get' or 'put' as the operation")

        if operation.lower() == "get":
            self.stdout.write(f"Fetching {source_path} from bucket {bucket_name}, saving to {dest_path}")
            bucket.download_file(source_path, dest_path)
            self.stdout.write(
                f"Done! Your file should be at {dest_path}"
            )    
        if operation.lower() == "put":
            self.stdout.write(f"Putting {source_path} into bucket {bucket_name}, and path {dest_path}")
            bucket.upload_file(source_path, dest_path)    
            self.stdout.write(
            f"Done! Your file should be at bucket {bucket_name}, path: {dest_path}"
            )
        
            
        
