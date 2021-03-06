import subprocess
from datetime import date

from requests import request, HTTPError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from sqlite_utils import Database

from ...object_storage import public_url


_COMPRESSION_TYPES = {
    "gzip": (("gzip", "--force", "--best"), "gz"),
    "bzip2": (("bzip2", "--force", "--compress"), "bz2"),
}


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

    @staticmethod
    def compress_file(file_path: str, compression_type: str = "gzip") -> str:
        """
        Compress the file at file_path with gzip.
        Should compress a sqlite file down to ~25% of original size.
        """
        if compression_type not in _COMPRESSION_TYPES:
            raise Exception((
                f'The "{compression_type}" is not supported. Use one '
                'of "%s".' % ('", "'.join(_COMPRESSION_TYPES.keys()))
            ))

        arguments, file_extension = _COMPRESSION_TYPES[compression_type]
        archive_path = f"{file_path}.{file_extension}"
        compression_process = subprocess.run([*arguments, archive_path])

        if compression_process.returncode > 0:
            raise Exception(f'Failed to compress "{file_path}" using "{compression_type}".')

        return archive_path

    @staticmethod
    def delete_files(*file_paths: str) -> None:
        subprocess.run(["rm", "-rf", *file_paths])

    @staticmethod
    def upload_file(file_path: str, bucket_name: str) -> None:
        upload_process = subprocess.run([
            "aws", "s3", "cp",
            "--acl", "public-read",
            file_path, f"s3://{bucket_name}/{file_path}",
        ])

        if upload_process.returncode > 0:
            raise Exception(f'Failed to upload "{file_path}".')

        try:
            access_check_response = request("head", public_url(bucket_name, file_path))

            if access_check_response.status_code != 200:
                raise Exception((
                    "The uploaded file is not publicly accessible "
                    f"(HTTP {access_check_response.status_code})."
                ))
        except HTTPError as error:
            raise Exception((
                "The status check request failed. Unable to determine "
                "whether the uploaded file is publicly available."
            )) from error


class Command(BaseCommand):
    help = "Dump green_domain table into sqlite."

    def add_arguments(self, parser):
        parser.add_argument("--upload", help="Also upload to Object Storage")

    def handle(self, *args, **options) -> None:
        exporter = GreenDomainExporter()
        db_name = f"green_urls_{date.today()}.db"

        exporter.export_to_sqlite(exporter.get_conn_string(), db_name)
        exporter.prepare_for_datasette(db_name)

        if options["upload"]:
            try:
                compressed_db_path = exporter.compress_file(db_name)

                exporter.upload_file(compressed_db_path, settings.DOMAIN_SNAPSHOT_BUCKET)
                exporter.delete_files(compressed_db_path, db_name)
            except Exception as error:
                raise CommandError(str(error)) from error
