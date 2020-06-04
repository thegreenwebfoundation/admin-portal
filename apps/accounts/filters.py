from django.contrib.admin import SimpleListFilter
from django_countries.data import COUNTRIES
from datetime import datetime
from django.utils import timezone

class YearFilterMixin():

    def last_15_years(self):
        current_year = datetime.now().year

        return ((f"{current_year - x}", f"{current_year - x}") for x in range(15))

    def lookups(self, request, model_admin):
        return self.last_15_years()

    def year_to_range(self, year: str= None):
        """
        Pass in a string for a year, and return two timezone aware
        datetimes to use for things like range queries by date.
        """

        year = int(year)
        tz = timezone.get_current_timezone()
        start_at = datetime(year=year, month=1, day=1, tzinfo=tz)
        end_at = datetime(year=year+1, month=1, day=1, tzinfo=tz)

        return (start_at, end_at)

class YearDCFilter(YearFilterMixin, SimpleListFilter):
    title = 'Last approved datacentre'
    parameter_name = 'last_created_dc'

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset

        start_at, end_at = self.year_to_range(self.value())
        return queryset.filter(
            hostingproviderdatacenter__created_at__range=(start_at, end_at)
        )

class YearIPFilter(YearFilterMixin, SimpleListFilter):
    title = 'Last approved IP Range (sloooowww)'
    parameter_name = 'last_approved_ip'

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset

        start_at, end_at = self.year_to_range(self.value())
        return queryset.filter(
                greencheckipapprove__created__range=(start_at, end_at)
        )

class YearASNFilter(YearFilterMixin, SimpleListFilter):
    title = 'Last approved ASN submission'
    parameter_name = 'last_approved_asn'

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset

        start_at, end_at = self.year_to_range(self.value())
        return queryset.filter(
            greencheckasnapprove__created__range=(start_at, end_at)
        )

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
