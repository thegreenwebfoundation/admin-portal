from django.contrib import admin
from django.contrib.auth.admin import Group
from django.utils.translation import gettext_lazy as _
from logentry_admin.admin import (
    ActionListFilter,
    LogEntry,
    LogEntryAdmin,
)

from ..admin_site import greenweb_admin

class GroupListFilter(admin.SimpleListFilter):
    """
    Provide a filter to
    """

    title = _("Group")
    parameter_name = "user_group"

    def lookups(self, request, model_admin):
        """
        Allow filtering by the groups that have been assigned to
        user. If a user has been assigned multiple groups they will
        appear in both filter options.
        """
        groups = Group.objects.all()
        return ((group.id, str(group)) for group in groups)

    def queryset(self, request, queryset):
        """
        Filter the possible logentry results to ones
        where they were created by a user in the group
        provided by self.value()
        """
        if self.value():
            queryset = queryset.filter(user__groups__in=[int(self.value())])
        return queryset


class GWLogEntryAdmin(LogEntryAdmin):
    """
    As subclass of the LogEntry admin provided by the
    `django-logentry-admin`
    """

    # override our list of filters
    list_filter = [GroupListFilter, "content_type", ActionListFilter]


greenweb_admin.register(LogEntry, GWLogEntryAdmin)
