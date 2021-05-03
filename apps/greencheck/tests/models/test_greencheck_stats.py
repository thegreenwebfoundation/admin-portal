import logging
import pytest

from django.utils import timezone
from dateutil.relativedelta import relativedelta
from dateutil import rrule
from dramatiq.brokers import stub
import dramatiq

from ... import models as gc_models
from ... import choices as gc_choices
from ... import factories as gc_factories
from ... import tasks as gc_tasks

from ....accounts import models as ac_models

logger = logging.getLogger(__name__)
console = logging.StreamHandler()
logger.setLevel(logging.DEBUG)
logger.addHandler(console)


class TestGreencheckStatsDaily:
    @pytest.mark.parametrize(
        "date_to_check, expected_count",
        [
            (timezone.now() - relativedelta(days=1), 1),
            (timezone.now() - relativedelta(days=2), 0),
            (timezone.now() - relativedelta(days=0), 0),
        ],
    )
    def test_count_daily_checks(
        self,
        db,
        hosting_provider_with_sample_user: ac_models.Hostingprovider,
        green_ip: gc_models.GreencheckIp,
        client,
        date_to_check,
        expected_count,
    ):
        """
        Do we run a count of all the checks for the last day?
        """
        two_am_yesterday = timezone.now() + relativedelta(hours=2, days=-1)

        gc = gc_factories.GreencheckFactory.create(date=two_am_yesterday)
        logger.info(f"logger date: {gc.date}")

        stat, green_stat, grey_stat = gc_models.DailyStat.total_count(
            date_to_check=date_to_check
        )

        assert stat.count == expected_count

    @pytest.mark.parametrize(
        "date_to_check, expected_count",
        [
            (timezone.now() - relativedelta(days=1), 1),
            (timezone.now() - relativedelta(days=2), 0),
            (timezone.now() - relativedelta(days=0), 0),
        ],
    )
    def test_count_daily_by_provider(
        self,
        db,
        hosting_provider_with_sample_user: ac_models.Hostingprovider,
        green_ip: gc_models.GreencheckIp,
        client,
        date_to_check,
        expected_count,
    ):
        """
        Do we run a count of all the checks for the last day?
        """
        two_am_yesterday = timezone.now() + relativedelta(hours=2, days=-1)

        gc = gc_factories.GreencheckFactory.create(
            date=two_am_yesterday, hostingprovider=hosting_provider_with_sample_user.id
        )

        logger.info(f"logger date: {gc.date}")

        stat, green_stat, grey_stat = gc_models.DailyStat.total_count_for_provider(
            date_to_check=date_to_check,
            provider_id=hosting_provider_with_sample_user.id,
        )
        assert stat.count == expected_count
        assert grey_stat.count == expected_count
        assert green_stat.count == 0

    def test_count_daily_by_provider_green(
        self,
        db,
        hosting_provider_with_sample_user: ac_models.Hostingprovider,
        green_ip: gc_models.GreencheckIp,
        client,
    ):
        """
        We should see greem checks
        """
        two_am_yesterday = timezone.now() + relativedelta(hours=2, days=-1)
        date_to_check = timezone.now() - relativedelta(days=1)

        green_gc = gc_factories.GreencheckFactory.create(
            date=two_am_yesterday,
            hostingprovider=hosting_provider_with_sample_user.id,
            greencheck_ip=green_ip.id,
            ip=green_ip.ip_end,
            green=gc_choices.BoolChoice.YES,
        )
        stat, green_stat, grey_stat = gc_models.DailyStat.total_count_for_provider(
            date_to_check=date_to_check,
            provider_id=hosting_provider_with_sample_user.id,
        )

        assert stat.count == 1
        assert green_stat.count == 1
        assert grey_stat.count == 0


@pytest.mark.only
class TestGreencheckStatsGeneration:
    def _set_up_dates_for_last_week(self):

        # set up our date range
        seven_days_ago = timezone.now() - relativedelta(days=7)
        yesterday = timezone.now() - relativedelta(days=1)

        last_seven_days = rrule.rrule(
            freq=rrule.DAILY, dtstart=seven_days_ago.date(), until=yesterday.date()
        )
        return [date for date in last_seven_days]

    def test_create_range_for_stats(
        self,
        db,
        hosting_provider_with_sample_user: ac_models.Hostingprovider,
        green_ip: gc_models.GreencheckIp,
        client,
    ):
        """
        Create a collection of daily stats, for a range of dates provided
        """

        generated_dates = self._set_up_dates_for_last_week()
        generated_stats = gc_models.DailyStat.create_counts_for_date_range(
            generated_dates, "total_count"
        )
        assert len(generated_stats) == len(generated_dates)

    def test_create_range_for_stats_async(
        self,
        transactional_db,
        broker: stub.StubBroker,
        worker: dramatiq.Worker,
        hosting_provider_with_sample_user: ac_models.Hostingprovider,
        green_ip: gc_models.GreencheckIp,
        client,
    ):
        """
        Create a collection of daily stats, for a range of dates provided.

        """
        broker.declare_queue("default")
        generated_dates = self._set_up_dates_for_last_week()

        for date in generated_dates:
            gc = gc_factories.GreencheckFactory.create(
                date=date + relativedelta(hours=2)
            )
            # logger.info(f"gc {date}: {gc.__dict__}")

        logger.info(f"just this date: { generated_dates[0] }")

        gc_models.DailyStat.create_counts_for_date_range_async(
            generated_dates, "total_count"
        )

        # Wait for all the tasks to be processed
        broker.join("default")
        worker.join()

        green_stats = gc_models.DailyStat.objects.filter(
            green=gc_choices.BoolChoice.YES
        )
        grey_stats = gc_models.DailyStat.objects.filter(green=gc_choices.BoolChoice.NO)
        mixed_stats = gc_models.DailyStat.objects.exclude(
            green__in=[gc_choices.BoolChoice.YES, gc_choices.BoolChoice.NO]
        )

        # have we generated the expected stats per day?
        assert green_stats.count() == 7
        assert grey_stats.count() == 7
        assert mixed_stats.count() == 7

        # we should one count showing zero green checks for each day
        assert [stat.count for stat in green_stats] == [0, 0, 0, 0, 0, 0, 0]

        # mixed and grey should be the same
        assert [stat.count for stat in grey_stats] == [1, 1, 1, 1, 1, 1, 1]
        assert [stat.count for stat in grey_stats] == [1, 1, 1, 1, 1, 1, 1]

    def test_create_stat_async(
        self,
        transactional_db,
        broker: stub.StubBroker,
        worker: dramatiq.Worker,
        hosting_provider_with_sample_user: ac_models.Hostingprovider,
        green_ip: gc_models.GreencheckIp,
        client,
    ):
        """
        Create a collection of daily stats, for a range of dates provided,
        but have a worker create the stats asynchronously.
        """

        broker.declare_queue("default")
        assert gc_models.DailyStat.objects.count() == 0
        # set up our date range
        generated_dates = self._set_up_dates_for_last_week()

        for date in generated_dates:
            gc_factories.GreencheckFactory.create(date=date + relativedelta(hours=2))

        chosen_date = str(generated_dates[0].date())

        # we use the 'send' with the 'transactional_db' fixture here instead of db
        # because if we use the regular db fixture, the workers can not see what is
        # happening 'inside' this test. TODO: check that this really is the
        # explanation for this strange test behaviour

        gc_tasks.create_stat_async.send(
            date_string=chosen_date, query_name="total_count"
        )

        # import ipdb

        # ipdb.set_trace()

        # Wait for all the tasks to be processed
        broker.join(gc_tasks.create_stat_async.queue_name)
        worker.join()

        # import ipdb

        # ipdb.set_trace()

        # hae we generate the daily stats?
        assert gc_models.DailyStat.objects.count() == 3

        # do that they have the right date?
        for stat in gc_models.DailyStat.objects.all():
            assert str(stat.stat_date) == chosen_date

        # do the stats count up to what we expect?
        green_daily_stat = gc_models.DailyStat.objects.filter(
            green=gc_choices.BoolChoice.YES
        ).first()
        grey_daily_stat = gc_models.DailyStat.objects.filter(
            green=gc_choices.BoolChoice.NO
        ).first()
        mixed_daily_stat = gc_models.DailyStat.objects.exclude(
            green__in=[gc_choices.BoolChoice.YES, gc_choices.BoolChoice.NO]
        ).first()

        assert green_daily_stat.count == 0
        assert grey_daily_stat.count == 1
        assert mixed_daily_stat.count == 1

