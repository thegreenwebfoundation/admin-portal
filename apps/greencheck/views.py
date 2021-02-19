from datetime import date
from datetime import timedelta

from django.conf import settings
from google.cloud import storage
from django.views.generic.base import TemplateView

from . import object_storage

bucket = object_storage.green_domains_bucket()


class GreenUrlsView(TemplateView):
    template_name = "green_url.html"

    def fetch_urls(self):

        return [
            (obj.key, object_storage.public_url(obj)) for obj in bucket.objects.all()
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
