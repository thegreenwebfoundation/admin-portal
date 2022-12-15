import collections
import typing
from datetime import date, timedelta

import waffle
from dateutil.relativedelta import relativedelta
from django.db.models import Sum
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.generic.base import TemplateView
from taggit.models import Tag
import django_filters
from waffle.mixins import WaffleFlagMixin

from apps.accounts.models.hosting import Hostingprovider
from apps.greencheck.models.checks import GreenDomain
from apps.greencheck.models.stats import DailyStat

from ..accounts import models as ac_models
from . import choices as gc_choices
from . import models as gc_models
from . import object_storage
from .tests import dummy_greencheck_stat_data as dummy_data

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


class GreencheckStatsView(WaffleFlagMixin, TemplateView):

    template_name = "greencheck/stats_index.html"
    waffle_flag = "greencheck-stats"

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

        if not green_count:
            green_count = 0
        if not grey_count:
            grey_count = 0

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

    def _get_top_green_hosters(self, begin_at, end_at) -> typing.List[typing.Dict]:
        """
        Return a list of hosts, with a count of checks in this time period
        defined by the start and end dates
        """

        hosters = (
            gc_models.DailyStat.objects.daily_stats_for_provider()
            .filter(stat_date__gte=begin_at.date(), stat_date__lte=end_at.date())
            .order_by("-count")
        )

        enriched_hosters = []
        counter = collections.Counter()

        # aggregated_hoster_counts = (
        #     hosters.values("stat_key").annotate(total=Sum("count")).order_by("-count")
        # )[:10]

        for host in hosters:
            counter[host.stat_key] = host.count

        for hoster_stat in counter.most_common(10):
            stat_key, total = hoster_stat
            hoster_id = stat_key.replace("total_daily_checks:provider:", "")
            if hoster_id != "None":
                provider = Hostingprovider.objects.get(pk=hoster_id)
            else:
                provider = None
            enriched_hosters.append({"provider": provider, "count": total})

        return enriched_hosters

    def _get_top_green_domains(self, begin_at, end_at) -> typing.List[DailyStat]:
        """
        Return a list of domains, with the count of checks in this time period.
        """
        domains = gc_models.DailyStat.objects.daily_stats_for_domain().filter(
            stat_date__gte=begin_at.date(), stat_date__lte=end_at.date()
        )

        enriched_domains = []
        domain_counter = collections.Counter()

        # we use a counter instead of aggregating in the database query, because
        # django's annotation framework was adding a second group by clause, so we
        # didn't get grouping by domains
        for dom in domains:
            domain_counter[dom.stat_key] += dom.count

        for dom_count in domain_counter.most_common(10):
            stat_key, total = dom_count
            domain_name = stat_key.replace("total_daily_checks:domain:", "")

            # go from the domain to the provider
            green_domain = gc_models.GreenDomain.objects.get(url=domain_name)
            provider = green_domain.hosting_provider

            enriched_domains.append(
                {"domain": domain_name, "hosted_by": provider, "count": total}
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
            "top_green_hosters": self._get_top_green_hosters(thirty_days_ago, now),
            "top_green_domains": self._get_top_green_domains(thirty_days_ago, now),
        }

        context["stats"] = res

        return context


class ProviderFilter(django_filters.FilterSet):
    """
    A filter set class to support filtering by
    name, services provided and the country a provider is based in.
    for more about django filter see:
    https://django-filter.readthedocs.io/en/main/
    """

    services = django_filters.ModelChoiceFilter(
        field_name="services",
        label="Services offered",
        queryset=Tag.objects.all(),
    )
    name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Hostingprovider
        fields = ["services", "country", "name"]


class DirectoryView(WaffleFlagMixin, TemplateView):
    """
    A view for filtering our list of providers by various criteria
    """

    template_name = "greencheck/directory_index.html"
    waffle_flag = "directory_listing"

    def get_context_data(self, *args, **kwargs):
        """
        Populate the page context with the filtered list
        of providers
        """

        queryset = Hostingprovider.objects.filter(showonwebsite=True).prefetch_related(
            "services"
        )

        ctx = super().get_context_data(**kwargs)

        # We need to pass in our request.GET object to know which filters
        # to apply, and our queryset is needed to know what pre-existing filters
        # are required
        filter_results = ProviderFilter(
            self.request.GET,
            queryset=queryset,
            request=self.request,
        )

        ctx["filter"] = filter_results

        return ctx
