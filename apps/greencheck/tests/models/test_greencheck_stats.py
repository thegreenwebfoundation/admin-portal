import pytest
from ... import choices, models

from django.utils import timezone
from dateutil.relativedelta import relativedelta

import logging
from typing import List

from ...models import GreencheckIp, Hostingprovider, DailyStat
from ...factories import GreencheckFactory


class TestGreencheckStatsDaily:
    @pytest.mark.only
    def test_count_daily_checks(
        self,
        db,
        hosting_provider_with_sample_user: Hostingprovider,
        green_ip: GreencheckIp,
        client,
    ):
        """
        Do we run a count of all the checks for the last day?
        """
        yesterday = timezone.now() - relativedelta(days=1)
        two_am = yesterday + relativedelta(hours=2)

        GreencheckFactory.create(date=two_am)

        gcst = DailyStat.total_count(date_to_check=yesterday.date())
        assert gcst == 1
