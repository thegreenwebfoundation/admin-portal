from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.views.generic.base import TemplateView

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

    def get_context_data(self, **kwargs):
        """
        Fetch the context for making our charts, and dashboards
        """
        context = super().get_context_data(**kwargs)

        query_name = self.request.GET.get("query_name")

        if query_name is None:
            query_name = gc_choices.DailyStatChoices.DAILY_TOTAL

        now = timezone.now()
        last_thirty_days = now - relativedelta(days=30)
        last_thirty_days_of_stats = (
            gc_models.DailyStat.objects.daily_stats()
            .filter(stat_date__gte=last_thirty_days.date())
            .order_by("-stat_date")
        )
        yesterday_stats = last_thirty_days_of_stats.filter(
            stat_date=now - relativedelta(days=1)
        )
        # import ipdb ; ipdb.set_trace()
        last_green = yesterday_stats.get(green="yes")
        last_grey = yesterday_stats.get(green="no")
        # import ipdb ; ipdb.set_trace()

        total_count = last_grey.count + last_green.count
        if total_count == 0:
            percentage_green = f"{0:.{1}%}"
        else:
            percentage_green = (
                f"{last_green.count /  (last_grey.count + last_green.count):.{1}%}"
            )

        chart_data = [
            {"x": str(datum.stat_date), "y": datum.count}
            for datum in last_thirty_days_of_stats
        ]

        res = {
            "headlines": {
                "percentage_green": percentage_green,
                "day_green": last_green.count,
                "day_grey": last_grey.count,
            },
            "chart_data": chart_data,
        }
        top_green_hosters = []
        for row in dummy_data.top_green_hosters:
            top_green_hosters.append(
                {
                    "provider": ac_models.Hostingprovider.objects.get(
                        pk=row["hoster_id"]
                    ),
                    "count": row["count"],
                }
            )

        context["stats"] = res
        context["top_green_domains"] = dummy_data.top_green_domains
        context["top_green_hosters"] = top_green_hosters

        # import ipdb ; ipdb.set_trace()

        return context
