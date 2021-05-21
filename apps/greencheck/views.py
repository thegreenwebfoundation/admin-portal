from apps.greencheck.models.checks import GreenDomain
from apps.accounts.models.hosting import Hostingprovider
from apps.greencheck.models.stats import DailyStat
import typing
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.views.generic.base import TemplateView

from django.db.models import Sum
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from . import models as gc_models
from . import choices as gc_choices
from ..accounts import models as ac_models
from .tests import dummy_greencheck_stat_data as dummy_data

import waffle

from . import object_storage

bucket = object_storage.green_domains_bucket()


class GreenUrlsView(TemplateView):
    template_name = "green_url.html"

    def fetch_urls(self):
        """
        Fetch the name, link pairs required to iterate through
        the downloadable snapshots in the admin.
        Returns a list of two-tuples, containing a filename and link.
        """
        return [
            (obj.key, object_storage.public_url(obj.bucket_name, obj.key))
            for obj in bucket.objects.all()
        ]

    @property
    def urls(self):
        """
        Setting the date two weeks in the future. Two weeks from now on
        it will prefetch the urls again
        """
        accessed_date = getattr(self, "_date", None)
        if not accessed_date or self._date < date.today():
            self._date = date.today() + timedelta(weeks=2)
            self._urls = self.fetch_urls()
        return self._urls

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["urls"] = self.urls
        return context


class GreencheckStatsView(TemplateView):

    template_name = "greencheck/stats_index.html"

    def get(self, request, *args, **kwargs):
        if waffle.flag_is_active(request, "greencheck-stats"):
            return super().get(request, args, kwargs)
        else:
            return HttpResponseRedirect(reverse("greenweb_admin:index"))

    def _get_headline_counts(self, daily_stat_queryset=None):
        """
        Accept a DailyStat queryset and return a dict of the aggregated counts
        from queryset
        """

        green_count = daily_stat_queryset.filter(green="yes").aggregate(
            total=Sum("count")
        )["total"]

        grey_count = daily_stat_queryset.filter(green="no").aggregate(
            total=Sum("count")
        )["total"]

        total_count = grey_count + green_count

        if total_count == 0:
            percentage_green = f"{0:.{1}%}"
        else:
            percentage_green = f"{green_count /  (grey_count + green_count):.{1}%}"

        return {
            "green_count": green_count,
            "grey_count": green_count,
            "percentage_green": percentage_green,
        }

    def _get_top_green_hosters(self, begin_at, end_at) -> typing.List:
        """
        Return a list of hosts, the count of checks in this time period

        """

        hosters = (
            gc_models.DailyStat.objects.daily_stats_for_provider()
            .filter(stat_date__gte=begin_at.date(), stat_date__lte=end_at.date())
            .order_by("-count")
        )

        enriched_hosters = []

        for hoster_stat in hosters:
            hoster_id = hoster_stat.stat_key.replace("total_daily_checks:provider:", "")
            hp = Hostingprovider.objects.get(pk=hoster_id)
            enriched_hosters.append({"provider": hp, "count": hoster_stat.count})

        return enriched_hosters

    def _get_top_green_domains(self, begin_at, end_at) -> typing.List[DailyStat]:
        """
        Return a list of domains, with the count of checks in this time period.

        """
        domains = (
            gc_models.DailyStat.objects.daily_stats_for_domain()
            .filter(stat_date__gte=begin_at.date(), stat_date__lte=end_at.date())
            .order_by("-count")
        )

        enriched_domains = []

        for domain in domains:
            domain_name = domain.stat_key.replace("total_daily_checks:domain:", "")
            # go from the domain to the provider
            green_dom = gc_models.GreenDomain.objects.get(url=domain_name)

            hp = ac_models.Hostingprovider.objects.get(pk=green_dom.hosted_by_id)
            enriched_domains.append(
                {"domain": domain_name, "provider": hp, "count": domain.count}
            )

        return enriched_domains

    def get_context_data(self, **kwargs):
        """
        Fetch the context for making our charts, and dashboards
        """
        context = super().get_context_data(**kwargs)

        query_name = self.request.GET.get("query_name")

        if query_name is None:
            query_name = gc_choices.DailyStatChoices.DAILY_TOTAL

        now = timezone.now()
        thirty_days_ago = now - relativedelta(days=30)

        last_thirty_days_of_stats = (
            gc_models.DailyStat.objects.daily_stats()
            .filter(stat_date__gte=thirty_days_ago.date(), stat_date__lte=now)
            .order_by("-stat_date")
        )

        headline_counts = self._get_headline_counts(last_thirty_days_of_stats)

        chart_data = {
            "green": [
                {"x": str(datum.stat_date), "y": datum.count}
                for datum in last_thirty_days_of_stats
                if datum.green == "yes"
            ],
            "grey": [
                {"x": str(datum.stat_date), "y": datum.count}
                for datum in last_thirty_days_of_stats
                if datum.green == "no"
            ],
        }

        res = {
            "headlines": {
                "percentage_green": headline_counts["percentage_green"],
                "green": headline_counts["green_count"],
                "grey": headline_counts["grey_count"],
            },
            "chart_data": chart_data,
            "top_green_hosters": self._get_top_green_hosters(now, thirty_days_ago),
            "top_green_domains": self._get_top_green_domains(now, thirty_days_ago),
        }

        context["stats"] = res

        return context
