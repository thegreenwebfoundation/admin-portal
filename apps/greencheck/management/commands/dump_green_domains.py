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

    def get_conn_string(self):
        """
        Fetch the connection string from the point of view of django settings.
        We use this to account for it being changed in testing.
        """
        db = settings.DATABASES["default"]
        # change this if we ever leave mysql, obvs
        return f"mysql://{db['USER']}:{db['PASSWORD']}@{db['HOST']}/{db['NAME']}"

    def export_to_sqlite(self, database_url: str, db_name: str):
        return subprocess.run(
            ["db-to-sqlite", database_url, db_name, "--table=greendomain"]
        )

    def prepare_for_datasette(self, db_name: str):
        """
        Make sure we have the indexes we need for use in datasette
        """
        db = Database(db_name)
        green_domains_table = db["greendomain"]
        # green_domains_table.create_index(["hosted_by"])

    def compress_file(self, file_path: str):
        """
        Compress the file at file_path with gzip.
        Should compress a sqlite file down to ~25% of original size.
        """
        subprocess.run(["gzip", "--force", file_path])

    def delete_file(self, file_path: str):
        subprocess.run(["rm", "-rf", file_path])

    def upload_file(self, file_path: str, file_destination: str):
        subprocess.run(["aws", "s3", "cp", file_path, file_destination])


class Command(BaseCommand):
    help = "Dump green_domain table into sqlite."

    def add_arguments(self, parser):
        parser.add_argument("--upload", help="Also upload to Object Storage")

    def handle(self, *args, **options):

        exporter = GreenDomainExporter()

        root = Path(settings.ROOT)

        conn_string = exporter.get_conn_string()
        today = date.today()
        db_name = f"green_urls_{today}.db"

        exporter.export_to_sqlite(conn_string, db_name)
        exporter.prepare_for_datasette(db_name)

        upload = options["upload"]
        if upload:
            bucket_name = settings.DOMAIN_SNAPSHOT_BUCKET
            compressed_db_path = f"{db_name}.gz"
            destination_path = f"s3://{bucket_name}/{compressed_db_path}"

            exporter.compress_file(db_name)
            exporter.upload_file(compressed_db_path, destination_path)

            # tidy up after ourselves
            exporter.delete_file(compressed_db_path)
            exporter.delete_file(db_name)

