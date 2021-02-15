import subprocess
import os
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from sqlite_utils import Database


class GreenDomainExporter:
    """
    Exports a snapshot of the green domains, to use for bulk exports
    or making available for analysis and browsing via Datasette.
    """



class Command(BaseCommand):
    help = "Dump green_domain table into sqlite."

    def add_arguments(self, parser):
        parser.add_argument("--upload", help="Also upload to Object Storage")

    def handle(self, *args, **options):
        root = Path(settings.ROOT)
        database_url = os.environ.get("DATABASE_URL")
        today = date.today()
        db_name = f"green_urls_{today}.db"

        exporter = GreenDomainExporter()

        subprocess.run(["db-to-sqlite", database_url, db_name, "--table=green_domains"])

        db = Database(db_name)
        green_domains_table = db["green_domains"]
        green_domains_table.create_index(["url"])
        green_domains_table.create_index(["hosted_by"])

        upload = options["upload"]
        if upload:
            bucket_name = settings.PRESENTING_BUCKET
            compressed_db_path = f"{db_name}.gz"
            destination_path = f"s3://{bucket_name}/{db_name}"

            exporter.compress_file(db_name)
            exporter.upload_file(db_name, destination_path)

            # tidy up after ourselves
            exporter.delete_file(compressed_db_path)

    def compress_file(self, file_path: str):
        """
        Compress the file at file_path with gzip.
        Should compress a sqlite file down to ~25% of original size.
        """
        subprocess.run("gzip", file_path)

    def delete_file(self, file_path):
        subprocess.run("rm", file_path)

    def upload_file(self, file_path, file_destination):
        subprocess.run("aws", "s3", "cp", file_path, file_destination)
