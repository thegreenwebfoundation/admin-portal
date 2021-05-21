import logging
import pytest
import io
from django.core import management

from ... import models as gc_models
from ... import choices as gc_choices
from ... import factories as gc_factories
from ... import tasks as gc_tasks
from ...management.commands import backfill_stats


logger = logging.getLogger(__name__)
console = logging.StreamHandler()
# logger.setLevel(logging.DEBUG)
# logger.addHandler(console)

FIRST_OF_JAN = "2020-01-01"
END_OF_JAN = "2020-01-31"


class TestStatManagement:
    @pytest.mark.parametrize(
        "start_date, end_date, no_of_days",
        [(FIRST_OF_JAN, END_OF_JAN, 31), (FIRST_OF_JAN, FIRST_OF_JAN, 1)],
    )
    def test_backfill_generate_dates(self, start_date, end_date, no_of_days):
        """
        Check that we can backfill our stats from our management commands.
        """

        sg = backfill_stats.StatGenerator()

        dates = sg._generate_inclusive_date_list(start_date, end_date)

        assert len(dates) == no_of_days

    def test_backfill_generate_jobs(self, db):
        """
        Check that we generate the expected jobs to be
        finished by a worker
        """

        sg = backfill_stats.StatGenerator()

        jobs = sg.generate_query_jobs_for_date_range(
            start_date_string=FIRST_OF_JAN,
            end_date_string=END_OF_JAN,
            query_name="daily_total",
        )

        assert len(jobs) == 31

    def test_backfill_top_domains(self, db):
        """
        Test that we can generate the jobs to be picked up
        by workers.
        """

        sg = backfill_stats.StatGenerator()

        jobs = sg.generate_query_jobs_for_date_range(
            start_date_string=FIRST_OF_JAN,
            end_date_string=FIRST_OF_JAN,
            query_name="total_count_for_domains",
        )

        assert len(jobs) == 1

    def test_calling_command(self, db):
        out = io.StringIO()
        management.call_command(
            "backfill_stats", FIRST_OF_JAN, FIRST_OF_JAN, stdout=out
        )

        assert (
            f"Queued up daily 'total_count' queries from {FIRST_OF_JAN} to {FIRST_OF_JAN}"
            in out.getvalue()
        )

    def test_calling_command_for_providers(self, db):
        out = io.StringIO()
        management.call_command(
            "backfill_stats",
            FIRST_OF_JAN,
            FIRST_OF_JAN,
            "--query",
            "total_count_for_providers",
            stdout=out,
        )

        assert "OK" in out.getvalue()

    def test_calling_command_for_domains(self, db):
        """
        Test that we can generate the rankings for top doamains for the given days
        """
        out = io.StringIO()
        management.call_command(
            "backfill_stats",
            FIRST_OF_JAN,
            FIRST_OF_JAN,
            "--query",
            "total_count_for_domains",
            stdout=out,
        )

