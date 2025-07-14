from datetime import date, timedelta

import django_filters
from django.views.generic.base import TemplateView

from apps.accounts.models.hosting import Hostingprovider

from ..accounts import models as ac_models
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


class ProviderFilter(django_filters.FilterSet):
    """
    A filter set class to support filtering by
    name, services provided and the country a provider is based in.
    for more about django filter see:
    https://django-filter.readthedocs.io/en/main/
    """

    services = django_filters.ModelChoiceFilter(
        field_name="services",
        label="Green web hosting service",
        # we exclude the "other" service, because it's only used
        # when a provider enters data, and we don't want to filter for it
        queryset=ac_models.Service.objects.exclude(slug="other-none"),
    )
    # note: this is commented out for Han,
    # name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Hostingprovider
        fields = ["services", "country"]


class DirectoryView(TemplateView):
    """
    A view for filtering our list of providers by various criteria
    """

    template_name = "greencheck/directory_index.html"

    def get_context_data(self, *args, **kwargs):
        """
        Populate the page context with the filtered list
        of providers
        """

        queryset = Hostingprovider.objects.filter(
            is_listed=True,
            archived=False
        ).prefetch_related(
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

        def provider_country_name(provider) -> str:
            """
            Return the country name for a provider. Used for sorting
            providers by their localised name, because by default, countries
            are sorted by their country code, i.e DE (Germany)
            before DK (Denmark)
            """
            if provider.country:
                return provider.country.name
            else:
                return "Unknown"

        # we include the filter in our context to allow the template to render
        # the filter form, even if we display the results using `ordered_results`
        # variable
        ctx["filter"] = filter_results

        # filter by country, and then within each country, filter by alphabetical order
        ordered_results_qs = filter_results.qs.order_by("country", "name")
        # now filter the top level country results by written country name
        # so we have Denmark listed before Germany for example, and so on.
        ctx["ordered_results"] = sorted(ordered_results_qs, key=provider_country_name)

        return ctx
