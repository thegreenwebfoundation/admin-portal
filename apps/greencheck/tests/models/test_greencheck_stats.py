import logging
import pytest

from django.utils import timezone
from dateutil.relativedelta import relativedelta


from ... import models as gc_models
from ... import choices as gc_choices
from ... import factories as gc_factories


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
        hosting_provider_with_sample_user: gc_models.Hostingprovider,
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
        hosting_provider_with_sample_user: gc_models.Hostingprovider,
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
        hosting_provider_with_sample_user: gc_models.Hostingprovider,
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

