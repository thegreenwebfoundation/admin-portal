import subprocess
from datetime import date
from typing import List

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

    @staticmethod
    def get_conn_string() -> str:
        """
        Fetch the connection string from the point of view of django settings.
        We use this to account for it being changed in testing.
        """
        db = settings.DATABASES["default"]
        # change this if we ever leave mysql, obvs
        return f"mysql://{db['USER']}:{db['PASSWORD']}@{db['HOST']}/{db['NAME']}"

    @classmethod
    def export_to_sqlite(cls, database_url: str, db_name: str) -> None:
        cls._subprocess(
            ["db-to-sqlite", database_url, db_name, "--table=greendomain"],
            f'Failed to export the "{db_name}" database to SQLite.'
        )

    @staticmethod
    def prepare_for_datasette(db_name: str) -> None:
        """
        Make sure we have the indexes we need for use in datasette
        """
        db = Database(db_name)
        green_domains_table = db["greendomain"]
        # green_domains_table.create_index(["hosted_by"])

    @classmethod
    def compress_file(cls, file_path: str, compression_type: str = "gzip") -> str:
        """
        Compress the file at `file_path` with `gzip` or `bzip2`.

        :param file_path: The path to file to compress.
        :param compression_type: The one of compression types.
        :returns: The path to created archive.
        :raises Exception: When `compression_type` is invalid.
        :raises RuntimeError: When the compression process fails.
        """
        if compression_type not in _COMPRESSION_TYPES:
            raise Exception((
                f'The "{compression_type}" is not supported. Use one '
                'of "%s".' % ('", "'.join(_COMPRESSION_TYPES.keys()))
            ))

        arguments, file_extension = _COMPRESSION_TYPES[compression_type]
        archive_path = f"{file_path}.{file_extension}"

        cls._subprocess(
            [*arguments, archive_path],
            f'Failed to compress "{file_path}" using "{compression_type}".',
        )

        return archive_path

    @classmethod
    def delete_files(cls, *file_paths: str) -> None:
        """
        Delete the given files.

        :param file_paths: The paths to files to remove.
        :raises RuntimeError: When the deletion process fails.
        """
        cls._subprocess(
            ["rm", "-f", *file_paths],
            'Failed to remove these files: "%s".' % ('", "'.join(file_paths)),
        )

    @classmethod
    def upload_file(cls, file_path: str, bucket_name: str) -> None:
        """
        Upload the file at `file_path` to the S3 bucket.

        :param file_path: The path to file to upload.
        :param bucket_name: The name of the S3 bucket to upload to.
        :raises RuntimeError: When the upload process fails or if the
         uploaded file cannot be accessed publicly.
        """
        cls._subprocess(
            [
                "aws", "s3", "cp", "--acl", "public-read",
                file_path, f"s3://{bucket_name}/{file_path}",
            ],
            f'Failed to upload the "{file_path}" to "{bucket_name}" S3 bucket.',
        )

        try:
            access_check_response = request("head", public_url(bucket_name, file_path))

            if access_check_response.status_code != 200:
                raise RuntimeError((
                    "The uploaded file is not publicly accessible "
                    f"(HTTP {access_check_response.status_code})."
                ))
        except HTTPError as error:
            raise RuntimeError((
                "The status check request failed. Unable to determine "
                "whether the uploaded file is publicly available."
            )) from error

    @staticmethod
    def _subprocess(args: List[str], error: str) -> None:
        process = subprocess.run(args, capture_output=True)

        if process.returncode > 0:
            raise RuntimeError(f"{error}\n------------------\n{process.stderr.decode('utf8')}")


class Command(BaseCommand):
    help = "Dump green_domain table into sqlite."

    def add_arguments(self, parser):
        parser.add_argument("--upload", help="Also upload to Object Storage")

    def handle(self, *args, **options) -> None:
        try:
            exporter = GreenDomainExporter()
            db_name = f"green_urls_{date.today()}.db"

            exporter.export_to_sqlite(exporter.get_conn_string(), db_name)
            exporter.prepare_for_datasette(db_name)

            if options["upload"]:
                compressed_db_path = exporter.compress_file(db_name)

                exporter.upload_file(compressed_db_path, settings.DOMAIN_SNAPSHOT_BUCKET)
                exporter.delete_files(compressed_db_path, db_name)
        except Exception as error:
            raise CommandError(str(error)) from error
