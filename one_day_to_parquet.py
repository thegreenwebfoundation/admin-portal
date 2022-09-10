import csv
import datetime
import logging
import pathlib
import tempfile

import duckdb
from dateutils import timedelta


from django.utils import timezone  # noqa

from apps.greencheck.models import checks  # noqa
from apps.greencheck.object_storage import object_storage_bucket  # noqa

logger = logging.getLogger(__name__)
infra_bucket = object_storage_bucket("internal-infra")


def csv_of_checks_for_day(day: datetime.date, csv_path: str) -> bool:
    """
    Run a query extracting the checks for the given day, and write the results
    date stamped csv file .
    If a directory is given, output the file into the given directory.
    """

    logger.info(f"Starting export for {day}")
    start_time = timezone.now()

    one_day_forward = timedelta(days=1)
    one_day_back = timedelta(days=-1)

    res = (
        checks.Greencheck.objects.filter(
            date__gt=day + one_day_back, date__lt=day + one_day_forward
        )
        .values_list()
        .iterator()
    )

    logger.info(f"Writing query results to {csv_path}")

    with open(csv_path, "w") as f:
        list_writer = csv.writer(f)
        for check in res:
            list_writer.writerow(check)

    logger.info(f"Finished export for {day}")

    end_time = timezone.now()
    logger.info(end_time)

    time_span = end_time - start_time
    logger.info(f"Took {time_span.seconds} seconds")

    return True


def convert_csv_to_parquet(csv_path: str, parquet_path: str) -> bool:
    """
    Load a CSV file at the path of `prefix/YYYY_MM_DD.csv`, and
    create a compressed parquet file at the path
    `prefix/YYYY_MM_DD.zstd.parquet`.
    If a directory is given, look inside it for the csv, and output
    the parquet file into it.
    """

    start_time = timezone.now()
    logger.info(f"Starting conversion to parquet for {csv_path}")
    logger.info(start_time)

    # set up our in-memory database with duckdb
    con = duckdb.connect(database=":memory:")

    # run our query to convert the day of checks to a compressed parquet file
    con.execute(
        (
            f"COPY (SELECT * from '{csv_path}') "
            f"TO '{parquet_path}' (FORMAT 'PARQUET', CODEC 'ZSTD')"
        )
    )
    logger.info(f"Finished conversion to parquet for {csv_path}")
    end_time = timezone.now()
    logger.info(end_time)

    time_span = end_time - start_time
    logger.info(f"Took {time_span.seconds} seconds")


def upload_to_object_storage(parquet_path: str, upload_path: str) -> bool:
    """
    Upload parquet file at `"prefix/YYYY_MM_DD.zstd.parquet" to object storage
    with the the key /parquet/days/TABLENAME_YYYY_MM_DD.zstd.parquet

    If a directory is provided, look in the directory for the parquet file.
    """
    start_time = timezone.now()
    logger.info(f"Start uploading at {start_time}")

    infra_bucket.upload_file(parquet_path, upload_path)

    end_time = timezone.now()
    time_span = end_time - start_time

    logger.info(f"Finished uploading at {end_time}")
    logger.info(f"Took {time_span.seconds} seconds")


def backup_day_to_parquet(target_date: datetime.date):
    """
    Accept a target date to back up, and then extract all
    the greenchecks for tha given day, and back up to object
    storage as a compressed parquet file.
    """

    # use a temporary directory, to clean up after ourselves
    # and avoid clashes
    with tempfile.TemporaryDirectory() as tmpdir:
        date_string = target_date.strftime("%Y-%m-%d")
        greencheck_table = "greencheck_2021"

        csv_path = f"{tmpdir}/{date_string}.local_file.csv"
        parquet_path = f"{tmpdir}/{date_string}.zstd.parquet"
        upload_path = f"parquet/days/{date_string}.{greencheck_table}.zstd.parquet"

        csv_of_checks_for_day(target_date, csv_path)
        convert_csv_to_parquet(csv_path, parquet_path)
        upload_to_object_storage(parquet_path, upload_path)
