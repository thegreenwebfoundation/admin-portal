from datetime import date
from datetime import timedelta

from django.conf import settings
from google.cloud import storage
from django.views.generic.base import TemplateView


class GreenUrlsView(TemplateView):
    template_name = "green_url.html"

    def fetch_urls(self):
        client = storage.Client()
        bucket_name = settings.DOMAIN_SNAPSHOT_BUCKET
        bucket = client.get_bucket(bucket_name)
        blobs = bucket.list_blobs()
        return [(b.name, b.public_url) for b in blobs]

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
