from django.contrib.admin import SimpleListFilter
from django_countries.data import COUNTRIES


class ShowWebsiteFilter(SimpleListFilter):
    title = 'shown on website'
    parameter_name = 'showwebsite'

    def lookups(self, request, model_admin):
        return (
            (True, 'Shown on website'),
            (False, 'Not shown on website'),
        )

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(showonwebsite=self.value())


class PartnerFilter(SimpleListFilter):
    title = 'partner'
    parameter_name = 'partner'

    def lookups(self, request, model_admin):
        return (
            (True, 'Partners'),
        )

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(partner=self.value())


class CountryFilter(SimpleListFilter):
    title = 'country'
    parameter_name = 'country'

    def lookups(self, request, queryset):
        from apps.accounts.models import Hostingprovider
        qs = Hostingprovider.objects.all().values_list('country', flat=True).distinct().order_by('country')
        countries = [(country, COUNTRIES.get(country, 'Unknown Country')) for country in qs]
        return countries

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(country=self.value())
