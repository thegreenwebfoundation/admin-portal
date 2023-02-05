import csv
import datetime
import logging
import tempfile
import duckdb
from dateutils import timedelta


from django.core.management.base import BaseCommand
from django.conf import settings

from django.utils import timezone  # noqa

from apps.greencheck.models import checks  # noqa
from apps.greencheck.object_storage import object_storage_bucket  # noqa

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    help = "Convert the compressed tsv file to parquet"

    def add_arguments(self, parser):
        parser.add_argument(
            "source_csv_path",
            type=str,
            help="the path to the tsv file for duckdb to read",
        )
        parser.add_argument(
            "destination_parquet_path",
            type=str,
            help=("the path to write the parquet file to"),
        )

    def convert_csv_to_parquet(self, csv_path: str, parquet_path: str) -> bool:
        """
        Load a CSV file at the path of `csv_path`, and
        create a compressed parquet file at the path
        `parquet_path`.
        """
        # set up our in-memory database with duckdb
        con = duckdb.connect(database=":memory:")

        # run our query to convert the day of checks to a compressed parquet file
        con.execute(
            (
                f"COPY (SELECT * from '{csv_path}') "
                f"TO '{parquet_path}' (FORMAT 'PARQUET', CODEC 'ZSTD')"
            )
        )

    def handle(self, *args, **options):

        file_path = options.get('source_csv_path')
        dest_path = options.get('destination_parquet_path')


        start_time = timezone.now()
        self.stdout.write(f"Starting conversion to parquet for {file_path}, at {start_time}")
        self.convert_csv_to_parquet(file_path, dest_path)

        end_time = timezone.now()

        self.stdout.write(
            f"Done at {end_time}! Your file should be at {dest_path}"
        )
