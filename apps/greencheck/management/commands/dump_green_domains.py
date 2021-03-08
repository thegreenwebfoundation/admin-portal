import subprocess
from datetime import date
from typing import List, Iterable

from requests import request, HTTPError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

from ...object_storage import public_url


_COMPRESSION_TYPES = {
    # Must be the first key to preserve the previous state
    # when it was the only and therefore default option.
    # Feel free to change this later if `bzip2` supersedes `gzip`.
    "gzip": (("gzip", "--force", "--best"), "gz"),
    "bzip2": (("bzip2", "--force", "--compress"), "bz2"),
}


class GreenDomainExporter:
    """
    Exports a snapshot of the green domains, to use for bulk exports
    or making available for analysis and browsing via Datasette.
    """

    TABLE = "greendomain"

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
    def export_to_sqlite(cls, database_url: str, db_path: str) -> None:
        """
        Export the `cls.TABLE` to `db_path` from given `database_url`.

        :param database_url: The database URL to export the `cls.TABLE` from.
        :param db_path: The path to file to export SQLite database to.
        """
        cls._subprocess(
            ["db-to-sqlite", database_url, db_path, f"--table={cls.TABLE}"],
            f'Failed to export the "{cls.TABLE}" table to "{db_path}" SQLite database.',
        )

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
            raise Exception(
                (
                    f'The "{compression_type}" compression is not supported. '
                    f"Use one of {cls._quote_items(_COMPRESSION_TYPES.keys())}."
                )
            )

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
            f"Failed to remove these files: {cls._quote_items(file_paths)}.",
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
                "aws",
                "s3",
                "cp",
                "--acl",
                "public-read",
                file_path,
                f"s3://{bucket_name}/{file_path}",
            ],
            f'Failed to upload the "{file_path}" to "{bucket_name}" S3 bucket.',
        )

        try:
            access_check_response = request("head", public_url(bucket_name, file_path))

            if access_check_response.status_code != 200:
                raise RuntimeError(
                    (
                        "The uploaded file is not publicly accessible "
                        f"(HTTP {access_check_response.status_code})."
                    )
                )
        except HTTPError as error:
            raise RuntimeError(
                (
                    "The status check request failed. Unable to determine "
                    "whether the uploaded file is publicly available."
                )
            ) from error

    @staticmethod
    def _subprocess(args: List[str], error: str) -> None:
        """
        Run a subprocess and raise a `RuntimeError` in case of a non-zero exit code.

        :param args: The command to run in a subprocess. See `subprocess.Popen`.
        :param error: The error message for the `RuntimeError` in case of
         failure. The `stderr` of the process will be appended.
        :raises RuntimeError: When the subprocess exits with a non-zero code.
        """
        process = subprocess.run(args, capture_output=True)

        if process.returncode > 0:
            raise RuntimeError(
                "\n".join(
                    [
                        error,
                        "------------------",
                        process.stderr.decode("utf8"),
                    ]
                )
            )

    @staticmethod
    def _quote_items(args: Iterable[str]) -> str:
        """
        Wrap each item of `args` into double-quotes and split them by comma.

        >>> GreenDomainExporter._quote_items(["test1", "test2", "test3"])
        '"test1", "test2", "test3"'

        :param args: The set of items to wrap members of.
        :returns: The stringified version of `args`.
        """
        return '"%s"' % '", "'.join(args)


class Command(BaseCommand):
    help = f'Dump the "{GreenDomainExporter.TABLE}" table into SQLite.'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--upload",
            help="Also upload to Object Storage",
            action="store_true",
            default=False,
        )

        for compression_type in _COMPRESSION_TYPES.keys():
            parser.add_argument(
                f"--{compression_type}",
                help=f'Compress SQLite dump using "{compression_type}".',
                dest="compression_type",
                const=compression_type,
                action="store_const",
                default=compression_type,
            )

    def handle(self, upload: bool, compression_type: str, *args, **options) -> None:
        try:
            db_path = f"green_urls_{date.today()}.db"
            exporter = GreenDomainExporter()
            exporter.export_to_sqlite(exporter.get_conn_string(), db_path)

            if upload:
                compressed_db_path = exporter.compress_file(
                    db_path,
                    compression_type,
                )

                exporter.upload_file(
                    compressed_db_path,
                    settings.DOMAIN_SNAPSHOT_BUCKET,
                )

                exporter.delete_files(
                    compressed_db_path,
                    db_path,
                )
        except Exception as error:
            raise CommandError(str(error)) from error
