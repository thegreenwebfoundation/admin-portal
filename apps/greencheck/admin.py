from django.contrib import admin, messages
from django.utils import translation
from django.utils.safestring import mark_safe

from apps.accounts.admin_site import greenweb_admin
from apps.accounts.models import Hostingprovider
from apps.accounts.utils import reverse_admin_name

from . import forms, models
from .choices import StatusApproval
from .forms import GreencheckIpApprovalForm, GreencheckIpForm
from .models import GreencheckIp, GreencheckIpApprove


class ApprovalFieldMixin:
    @mark_safe
    def approval(self, obj):
        if obj._meta.model_name == "greencheckasnapprove":
            name = "approval_asn"
        else:
            name = "approval_ip"

        approve_url = reverse_admin_name(
            Hostingprovider,
            name=name,
            params={"action": StatusApproval.APPROVED, "approval_id": obj.pk},
        )
        reject_url = reverse_admin_name(
            Hostingprovider,
            name=name,
            params={"action": StatusApproval.REMOVED, "approval_id": obj.pk},
        )

        approve = f'<a href="{approve_url}">Approve</a>'
        reject = f'<a href="{reject_url}">Reject</a>'
        link = f"{approve} / {reject}"
        action_taken = any(
            [
                obj.status == StatusApproval.DELETED,
                obj.status == StatusApproval.REMOVED,
                obj.status == StatusApproval.APPROVED,
            ]
        )
        if action_taken:
            return "Action taken"
        return link

    approval.short_description = "Decide"


class GreencheckAsnInline(admin.TabularInline):
    extra = 0
    form = forms.GreencheckAsnForm
    model = models.GreencheckASN
    ordering = ("asn",)
    verbose_name = "ASN"
    verbose_name_plural = "ASN"


class GreencheckAsnApproveInline(admin.TabularInline, ApprovalFieldMixin):
    extra = 0
    form = forms.GreencheckAsnApprovalForm
    model = models.GreencheckASNapprove
    ordering = ("asn",)
    verbose_name = "ASN approval"
    verbose_name_plural = "ASN approvals"

    readonly_fields = ("action", "status", "approval", "created")

    def get_fieldsets(self, request, obj=None):
        fields = (
            "created",
            "asn",
            "action",
            "status",
        )

        if request.user.is_staff:
            fields = fields + ("approval",)

        fieldsets = ((None, {"fields": fields}),)
        return fieldsets

    def get_readonly_fields(self, request, obj):
        """Non staff user should only be able to read the fields"""
        read_only = super().get_readonly_fields(request, obj)
        if not request.user.is_staff:
            read_only = ("asn",) + read_only
        return read_only


class GreencheckIpInline(admin.TabularInline):
    extra = 0
    form = GreencheckIpForm
    model = GreencheckIp
    ordering = (
        "ip_start",
        "ip_end",
    )
    verbose_name = "IP"
    verbose_name_plural = "IPs"


class GreencheckIpApproveInline(admin.TabularInline, ApprovalFieldMixin):
    extra = 0
    form = GreencheckIpApprovalForm
    model = GreencheckIpApprove
    ordering = (
        "ip_start",
        "ip_end",
    )
    verbose_name = "IP approval"
    verbose_name_plural = "IP approvals"

    readonly_fields = ("action", "status", "approval", "created")

    def get_fieldsets(self, request, obj=None):
        fields = (
            "created",
            "ip_start",
            "ip_end",
            "action",
            "status",
        )

        if request.user.is_staff:
            fields = fields + ("approval",)

        fieldsets = ((None, {"fields": fields}),)
        return fieldsets

    def get_readonly_fields(self, request, obj):
        """Non staff user should only be able to read the fields"""
        read_only = super().get_readonly_fields(request, obj)
        if not request.user.is_staff:
            read_only = ("ip_start", "ip_end") + read_only
        return read_only

    class Media:
        js = (
            "admin/js/vendor/jquery/jquery.js",
            "admin/js/jquery.init.js",
            "greencheck/js/email.js",
        )


class StatusIpFilter(admin.SimpleListFilter):
    title = "status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        qs = (
            GreencheckIpApprove.objects.all()
            .distinct()
            .values_list("status", flat=True)
        )
        status = [(s, s) for s in qs]
        return status

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(status=self.value())


class StatusAsFilter(admin.SimpleListFilter):
    title = "status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        qs = (
            GreencheckIpApprove.objects.all()
            .distinct()
            .values_list("status", flat=True)
        )
        status = [(s, s) for s in qs]
        return status

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(status=self.value())


@admin.register(GreencheckIpApprove, site=greenweb_admin)
class GreencheckIpApproveAdmin(admin.ModelAdmin):
    list_display = [
        "__str__",
        "link",
        "status",
        "created",
        "modified",
    ]

    list_display_links = None
    list_filter = [StatusIpFilter]
    readonly_fields = ["link"]
    actions = ["approve_selected"]

    def get_actions(self, request):
        """
        Return a list of the bulk actions the user should be able to do.
        """
        default_actions = super().get_actions(request)

        # only staff users should be able to to bulk updates

        if request.user and request.user.is_staff:

            return default_actions
        else:
            del default_actions["approve_selected"]
            return default_actions

    @admin.action(description="Approve selected green ip ranges")
    def approve_selected(self, request, queryset):
        """
        Accept a set of Green IP approval requests to
        process, and approve them.
        """
        approved_ips = [
            ip_range.process_approval(StatusApproval.APPROVED) for ip_range in queryset
        ]
        hosting_provider_names = set([ip.hostingprovider.name for ip in approved_ips])

        printable_names = ", ".join([name for name in hosting_provider_names])

        self.message_user(
            request,
            translation.ngettext(
                (
                    f"OK. {len(approved_ips)} green IP range have "
                    "been successfully updated for the following "
                    f"provider: {printable_names}"
                ),
                (
                    f"OK. {len(approved_ips)} green IP ranges have "
                    "been successfully updated for the following "
                    f"providers: {printable_names}"
                ),
                len(approved_ips),
            ),
            messages.SUCCESS,
        )

        return approved_ips

    def get_queryset(self, request):

        qs = super().get_queryset(request)
        qs = qs.select_related("hostingprovider")

        # only show a normal user's own requests
        if not request.user.is_staff:
            res = qs.filter(hostingprovider=request.user.hostingprovider)
            return res

        return qs

    @mark_safe
    def link(self, obj):
        url = reverse_admin_name(
            Hostingprovider, "change", kwargs={"object_id": obj.hostingprovider_id}
        )
        return '<a href="{}">Link to {}</a>'.format(url, obj.hostingprovider.name)

    link.short_description = "Link to Hostingprovider"


@admin.register(models.GreencheckASNapprove, site=greenweb_admin)
class GreencheckASNApprove(admin.ModelAdmin):
    list_display = [
        "__str__",
        "link",
        "status",
        "created",
        "modified",
    ]
    list_filter = [StatusAsFilter]
    list_display_links = None
    readonly_fields = ["link"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("hostingprovider")
        return qs

    @mark_safe
    def link(self, obj):
        url = reverse_admin_name(
            Hostingprovider, "change", kwargs={"object_id": obj.hostingprovider_id}
        )
        return '<a href="{}">Link to {}</a>'.format(url, obj.hostingprovider.name)

    link.short_description = "Link to Hostingprovider"

@admin.register(models.GreenDomain, site=greenweb_admin)
class GreenDomainAdmin(admin.ModelAdmin):
    list_display = [
        "url",
        "modified",
        "green",
        "hosted_by_website",
        "hosting_provider",
    ]
    search_fields = ("url", "hosted_by_website")
    fields = [
        "url",
        "hosted_by",
        "hosted_by_website",
        "hosted_by_id",
        "modified",
        "green",

    ]
