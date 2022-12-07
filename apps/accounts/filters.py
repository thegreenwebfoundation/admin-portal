from django.contrib.admin import SimpleListFilter
from django_admin_multiple_choice_list_filter.list_filters import (
    MultipleChoiceListFilter,
)
from django.contrib import messages


from django_countries.data import COUNTRIES
from datetime import datetime


class YearFilterMixin:
    def last_15_years(self):
        current_year = datetime.now().year

        return ((f"{current_year - x}", f"{current_year - x}") for x in range(15))

    def lookups(self, request, model_admin):
        return self.last_15_years()

    def year_to_range(self, year: str = None):
        """
        Pass in a string for a year, and return two timezone aware
        datetimes to use for things like range queries by date.
        """

        year = int(year)
        # TODO: while we use MySQL and the TIMESTAMP column we
        # can't use timezone aware dates. Put this back in when
        # we switch to columns or database tech
        # tz = timezone.get_current_timezone()
        start_at = datetime(year=year, month=1, day=1)
        end_at = datetime(year=year + 1, month=1, day=1)

        return (start_at, end_at)


class YearDCFilter(YearFilterMixin, SimpleListFilter):
    title = "Last approved datacentre"
    parameter_name = "last_created_dc"

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset

        start_at, end_at = self.year_to_range(self.value())
        return queryset.filter(
            hostingproviderdatacenter__created_at__range=(start_at, end_at)
        )


class YearIPFilter(YearFilterMixin, SimpleListFilter):
    title = "Last approved IP Range (sloooowww)"
    parameter_name = "last_approved_ip"

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset

        start_at, end_at = self.year_to_range(self.value())
        return queryset.filter(greencheckipapprove__created__range=(start_at, end_at))


class YearASNFilter(YearFilterMixin, SimpleListFilter):
    title = "Last approved ASN submission"
    parameter_name = "last_approved_asn"

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset

        start_at, end_at = self.year_to_range(self.value())
        return queryset.filter(greencheckasnapprove__created__range=(start_at, end_at))


class ShowWebsiteFilter(SimpleListFilter):
    title = "shown on website"
    parameter_name = "showwebsite"

    def lookups(self, request, model_admin):
        return (
            (True, "Shown on website"),
            (False, "Not shown on website"),
        )

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(showonwebsite=self.value())


class PartnerFilter(SimpleListFilter):
    title = "partner"
    parameter_name = "partner"

    def lookups(self, request, model_admin):
        return ((True, "Partners"),)

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(partner=self.value())


class CountryFilter(SimpleListFilter):
    title = "country"
    parameter_name = "country"

    def lookups(self, request, queryset):
        from apps.accounts.models import Hostingprovider

        qs = (
            Hostingprovider.objects.all()
            .values_list("country", flat=True)
            .distinct()
            .order_by("country")
        )
        countries = [
            (country, COUNTRIES.get(country, "Unknown Country")) for country in qs
        ]
        return countries

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(country=self.value())


class LabelFilter(MultipleChoiceListFilter):
    title = "Label"
    parameter_name = "label"

    def lookups(self, request, queryset):
        from apps.accounts.models import Label

        return [(label.slug, label.name) for label in Label.objects.all()]

    def queryset(self, request, queryset):
        """
        Filter the existing query by a the active tags.
        We need to do this in a somewhat awkward way to accomodate django
        taggit's query magic
        https://stackoverflow.com/questions/17436978/how-do-i-use-djangos-q-with-django-taggit

        """

        if self.value() is None:
            return queryset

        filter_vals = self.value().split(",")

        if len(filter_vals) == 1:
            return queryset.filter(staff_labels__slug__in=[filter_vals[0]])

        if len(filter_vals) == 2:
            first = queryset.filter(staff_labels__slug__in=[filter_vals[0]]).values(
                "id"
            )
            second = queryset.model.objects.filter(
                pk__in=first, staff_labels__slug__in=[filter_vals[1]]
            )
            return second

        if len(filter_vals) == 3:
            first = queryset.filter(staff_labels__slug__in=[filter_vals[0]]).values(
                "id"
            )
            second = queryset.model.objects.filter(
                pk__in=first, staff_labels__slug__in=[filter_vals[1]]
            ).values("id")
            third = queryset.model.objects.filter(
                pk__in=second, staff_labels__slug__in=[filter_vals[2]]
            )
            return third

        if len(filter_vals) == 4:
            first = queryset.filter(staff_labels__slug__in=[filter_vals[0]]).values(
                "id"
            )
            second = queryset.model.objects.filter(
                pk__in=first, staff_labels__slug__in=[filter_vals[1]]
            ).values("id")
            third = queryset.model.objects.filter(
                pk__in=second, staff_labels__slug__in=[filter_vals[2]]
            )
            fourth = queryset.model.objects.filter(
                pk__in=third, staff_labels__slug__in=[filter_vals[3]]
            )
            return fourth

        if len(filter_vals) > 4:
            warning_message = (
                "Sorry, this system does not support using more than 4 active filters"
                " at a time - no filtering by label has been applied. Please exclude"
                " some of your active label filters to reactivate filtering."
            )

            messages.add_message(request, messages.WARNING, warning_message)
            return []
