import logging

import dateutil.parser as date_parser
from dateutil import rrule
from django.conf import settings
from django.core.management.base import BaseCommand

from ... import models as gc_models

logger = logging.getLogger(__name__)
# console = logging.StreamHandler()
# logger.addHandler(console)
# logger.setLevel(logging.DEBUG)


class StatGenerator:
    """
    A wrapper class for generating a range of jobs
    """

    def _generate_inclusive_date_list(
        self, start_date: str = None, end_date: str = None
    ):
        """
        Generate a list of dates from two given date strings, inclusive of the
        dates provided
        """
        parsed_start_date = date_parser.parse(start_date)
        parsed_end_date = date_parser.parse(end_date)

        days_between_dates = rrule.rrule(
            freq=rrule.DAILY, dtstart=parsed_start_date, until=parsed_end_date
        )
        return [date for date in days_between_dates]

    def generate_query_jobs_for_date_range(
        self,
        start_date_string: str = None,
        end_date_string: str = None,
        query_name: str = None,
    ):
        """
        Accept the start date_string, end date_string, and the corresponding query
        method name on DailyStat to generate the requested stats.
        """

        inclusive_day_list = self._generate_inclusive_date_list(
            start_date_string, end_date_string
        )

        gc_models.DailyStat.clear_counts_for_date_range(
            inclusive_day_list, query_name=query_name
        )

        jobs = gc_models.DailyStat.create_counts_for_date_range_async(
            inclusive_day_list, query_name=query_name
        )

        return jobs


class Command(BaseCommand):

    sg = StatGenerator()

    help = (
        "Generate a set of daily stats for the provided date range. "
        "Accepts an optional query_name"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "start_date", type=str, help="The inclusive start date for generating stats"
        )
        parser.add_argument(
            "end_date", type=str, help="The inclusive end date for generating stats"
        )
        parser.add_argument(
            "-q",
            "--query",
            type=str,
            help="the chosen query to run against each date in the date range. Defaults to a daily total count of greenchecks",
        )

    def handle(self, *args, **options):
        """
        """

        start_date = options["start_date"]
        end_date = options["end_date"]

        query_name = options.get("query")
        if query_name is None:
            query_name = "total_count"

        self.sg.generate_query_jobs_for_date_range(
            start_date_string=start_date,
            end_date_string=end_date,
            query_name=query_name,
        )

        self.stdout.write(
            f"OK. Queued up daily '{query_name}' queries from {start_date} to {end_date}"
        )
