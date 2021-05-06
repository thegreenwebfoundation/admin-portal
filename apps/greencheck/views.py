from datetime import date, timedelta
from django.views.generic.base import TemplateView

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from . import models as gc_models
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

        # XX.X %
        percentage_green = f"{dummy_data.day_green /  dummy_data.day_total:.{1}%}"

        dummy_data.day_totals["percentage_green"] = percentage_green

        res = {
            "headline_stats": dummy_data.day_totals,
            "chart_data": dummy_data.counts_by_day,
        }

        context["stats"] = res

        return context
