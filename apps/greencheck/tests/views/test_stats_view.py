import functools
import logging

import faker
import pytest
from dateutil.relativedelta import relativedelta
from django import urls
from django.utils import timezone
from waffle.testutils import override_flag

from ....accounts import models as ac_models
from ... import choices as gc_choices
from ... import factories as gc_factories
from ... import models as gc_models
from .. import range_of_dates, view_in_browser

logger = logging.getLogger(__name__)
console = logging.StreamHandler()
# logger.setLevel(logging.DEBUG)
# logger.addHandler(console)
fake = faker.Faker()


class TestDailyStatsView:
    """
    Check that we render the right templates
    """

    def _setup_top_green_domains(self):
        """
        Set up a set of daily stats listing the top domains
        for a given date
        """

        yesterday = timezone.now() - relativedelta(days=1)
        thirty_days_back = timezone.now() - relativedelta(days=30)
        last_30_days = range_of_dates(thirty_days_back, yesterday)

        for x in range(10):
            realist_random_no = int(fake.numerify()) * int(fake.numerify())
            domain = fake.domain_name()

            for given_datetime in last_30_days:

                daily_total = gc_choices.DailyStatChoices.DAILY_TOTAL
                domain_key = f"{daily_total}:domain:{domain}"

                # set up domain to check against, with
                # corresponding hosting provider

                gc_factories.GreenDomainFactory(url=domain)

                gc_models.DailyStat.objects.create(
                    stat_key=domain_key,
                    count=realist_random_no,
                    green=gc_choices.GreenStatChoice.YES,
                    stat_date=given_datetime.date(),
                )

    def _get_top_green_hosters(self):
        """
        Set up a set of stats for the top providers for a
        given date
        """

        yesterday = timezone.now() - relativedelta(days=1)
        thirty_days_back = timezone.now() - relativedelta(days=30)
        last_30_days = range_of_dates(thirty_days_back, yesterday)

        for x in range(10):
            realist_random_no = int(fake.numerify()) * int(fake.numerify())
            provider_name = fake.company()

            for given_datetime in last_30_days:
                daily_total = gc_choices.DailyStatChoices.DAILY_TOTAL
                provider = gc_factories.HostingProviderFactory(name=provider_name)

                domain_key = f"{daily_total}:provider:{provider.id}"

                gc_models.DailyStat.objects.create(
                    stat_key=domain_key,
                    count=realist_random_no,
                    green=gc_choices.GreenStatChoice.YES,
                    stat_date=given_datetime.date(),
                )

    def _setup_30_days_of_stats_for_chart(
        self, hosting_provider_with_sample_user, green_ip
    ):
        # for each date, add one green and two grey checks for every day
        now = timezone.now()
        thirty_days_back = now - relativedelta(days=30)
        yesterday = now - relativedelta(days=1)
        last_30_days = range_of_dates(thirty_days_back, yesterday)

        for given_datetime in last_30_days:
            gc_factories.GreencheckFactory.create(
                date=given_datetime + relativedelta(hours=2),
                hostingprovider=hosting_provider_with_sample_user.id,
                greencheck_ip=green_ip.id,
                ip=green_ip.ip_end,
                green=gc_choices.BoolChoice.YES,
            )

            gc_factories.GreencheckFactory.create_batch(
                size=2, date=given_datetime + relativedelta(hours=2),
            )

        gc_models.DailyStat.create_counts_for_date_range(last_30_days, "total_count")

    @override_flag("greencheck-stats", active=True)
    def test_stat_view_templates(self, db, client):
        """
        Test that we render successfully and the write template
        """

        stat_path = urls.reverse("greencheck-stats-index")
        res = client.get(stat_path)

        assert res.status_code == 200
        assert "greencheck/stats_index.html" in [tmpl.name for tmpl in res.templates]

    @override_flag("greencheck-stats", active=True)
    def test_stat_view_headlines(
        self,
        db,
        client,
        hosting_provider_with_sample_user: ac_models.Hostingprovider,
        green_ip: gc_models.GreencheckIp,
    ):
        """
        Check that we have the aggregated headline figures available to us
        """

        self._setup_30_days_of_stats_for_chart(
            hosting_provider_with_sample_user, green_ip
        )

        stat_path = urls.reverse("greencheck-stats-index")
        res = client.get(stat_path)

        assert res.status_code == 200

        # do we have plausible numbers now?
        headlines = res.context_data["stats"]["headlines"]

        stats = [
            stat.count
            for stat in gc_models.DailyStat.objects.filter(
                stat_key="total_daily_checks", green="yes"
            )
        ]

        total_green = functools.reduce(lambda x, y: x + y, stats)

        assert headlines["green"] == total_green

    @override_flag("greencheck-stats", active=True)
    def test_stat_view_chart(
        self,
        db,
        hosting_provider_with_sample_user: ac_models.Hostingprovider,
        green_ip: gc_models.GreencheckIp,
        client,
    ):
        """
        Test that we fetch the last 30 days of stats, and make it avaiable for graphing
        """
        self._setup_30_days_of_stats_for_chart(
            hosting_provider_with_sample_user, green_ip
        )

        stat_path = urls.reverse("greencheck-stats-index")
        res = client.get(stat_path)

        assert res.status_code == 200

        stats = res.context_data["stats"]

        assert "headlines" in stats.keys()
        assert "chart_data" in stats.keys()

        chart_data = stats["chart_data"]

        # we want to see the green, grey, for our charts
        assert len(chart_data["green"]) == 30
        assert len(chart_data["grey"]) == 30

    @pytest.mark.flaky
    @override_flag("greencheck-stats", active=True)
    def test_stat_view_top_domains(
        self, db, client,
    ):
        """
        Test that we have can display a list of the top domains
        """

        self._setup_top_green_domains()

        stat_path = urls.reverse("greencheck-stats-index")
        res = client.get(stat_path)

        stats = res.context_data["stats"]

        assert "top_green_domains" in stats.keys()
        top_green_domains = stats["top_green_domains"]

        assert len(top_green_domains) == 10

    @override_flag("greencheck-stats", active=True)
    def test_stat_view_top_providers(self, db, client):
        """
        Test that we can display a list of the top domains
        """

        self._get_top_green_hosters()

        stat_path = urls.reverse("greencheck-stats-index")

        res = client.get(stat_path)

        stats = res.context_data["stats"]

        assert "top_green_hosters" in stats.keys()
        top_green_hosters = stats["top_green_hosters"]

        assert len(top_green_hosters) == 10

