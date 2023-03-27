from django.contrib import admin, messages

from django.utils import translation
from django.utils.safestring import mark_safe
from django.urls import path, reverse
from django.shortcuts import redirect, render


from apps.accounts.admin_site import greenweb_admin
from apps.accounts.models import Hostingprovider
from apps.accounts.utils import reverse_admin_name, get_admin_name


from . import forms, models
from .choices import StatusApproval
from .forms import GreencheckIpApprovalForm, GreencheckIpForm, GreenDomainAllocationForm
from .models import GreencheckIp, GreencheckIpApprove, GreenDomain


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

    actions = ["start_allocating_to_provider"]

    def get_actions(self, request):
        """
        Return a list of the bulk actions the user should be able to do.
        """
        default_actions = super().get_actions(request)

        # only staff users should be able to to bulk updates
        if request.user and request.user.is_staff:
            return default_actions
        else:
            del default_actions["allocate_to_provider"]
            return default_actions

    @admin.action(description="Allocate selected domains to new provider")
    def start_allocating_to_provider(self, request, queryset):
        """
        Accept a set of Green IP approval requests to
        process, and approve them.
        """
        domains = queryset.values_list("pk", flat=True)
        # allow for a form submission
        new_path = reverse("greenweb_admin:greencheck_greendomain_allocate_to_provider")

        from django.http import QueryDict

        qd = QueryDict(mutable=True)
        qd.setlist("domains", [dom for dom in domains])
        params = qd.urlencode()

        return redirect(f"{new_path}?{params}")

    def allocate_to_provider(self, request):
        """
        Accept a list of ids for green domains, and allocate
        them to the
        """

        ctx = {}
        form = None

        if request.POST:
            domain_ids = request.POST.getlist("domains")
            provider_id = request.POST.get("provider")

            form_data = {
                "domains": domain_ids,
                "provider": provider_id,
            }
            form = GreenDomainAllocationForm(form_data)

            if form.is_valid():
                form.save()
                domains = [dom.url for dom in form.cleaned_data["domains"]]
                provider = form.cleaned_data["provider"]

                self.message_user(
                    request,
                    translation.gettext(
                        (
                            "OK. The following domains have been allocated to "
                            f"provider: {provider} - {', '.join(domains)}"
                        ),
                    ),
                    messages.SUCCESS,
                )

                return redirect("greenweb_admin:greencheck_greendomain_changelist")

        domain_ids = request.GET.getlist("domains")
        if not domain_ids:
            self.message_user(
                request,
                translation.gettext(
                    (
                        "There were no domains given to allocate to a provider. "
                        "Please select at least one domain to re-allocate."
                    ),
                ),
                messages.WARNING,
            )
            return redirect("greenweb_admin:greencheck_greendomain_changelist")

        domains = GreenDomain.objects.filter(pk__in=domain_ids)
        ctx["domains"] = domains
        ctx["form"] = GreenDomainAllocationForm({"domains": domain_ids})

        return render(request, "allocate_domains_to_provider.html", ctx)

    def get_urls(self):
        """
        Add the needed urls for working wirth Green Domains
        """

        urls = super().get_urls()

        added = [
            path(
                "allocate_to_provider",
                self.allocate_to_provider,
                name=get_admin_name(self.model, "allocate_to_provider"),
            )
        ]
        return added + urls


@admin.register(models.GreencheckASN, site=greenweb_admin)
class GreenASNAdmin(admin.ModelAdmin):
    list_filter = [
        "active",
        "hostingprovider__archived",
        "hostingprovider",
    ]
    list_display = [
        "active",
        "asn",
        "hostingprovider",
        "created",
        "modified",
    ]
    search_fields = ["asn", "hostingprovider__name"]
    fields = ["active", "asn", "hostingprovider", "created", "modified"]
    readonly_fields = ["created", "modified"]

    def has_view_permission(self, request, obj=None):
        """
        Only allow staff to view AS numbers via the main django
        listing. We restrict this, to avoid end users seeing the list of
        other providers in the admin.
        """
        if request.user.is_admin:
            return True
        return False

    def has_add_permission(self, request):
        """
        We only allow staff to add AS numbers via the main django
        listing.
        Non-staff users need to use the hosting profile change view
        page instead.
        """
        if request.user.is_admin:
            return True
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("hostingprovider")

        # only show a normal user's own requests
        if not request.user.is_staff:
            res = qs.filter(hostingprovider=request.user.hostingprovider)
            return res

        return qs


@admin.register(models.GreencheckIp, site=greenweb_admin)
class GreenIPAdmin(admin.ModelAdmin):
    list_filter = [
        "active",
        "hostingprovider__archived",
        "hostingprovider",
    ]
    list_display = [
        "active",
        "ip_start",
        "ip_end",
        "hostingprovider",
        "created",
        "modified",
    ]
    search_fields = [
        "hostingprovider__name",
        "ip_start",
        "ip_end",
    ]
    fields = ["active", "ip_start", "ip_end", "hostingprovider", "created", "modified"]
    readonly_fields = ["created", "modified"]

    def has_view_permission(self, request, obj=None):
        """
        Only allow staff to view AS numbers via the main django
        listing. We restrict this, to avoid end users seeing the list of
        other providers in the admin.
        """
        if request.user.is_admin:
            return True
        return False

    def has_add_permission(self, request):
        """
        Like ASNs, only staff should be able to add IP ranges directly
        """
        if request.user.is_admin:
            return True
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("hostingprovider")

        # only show a normal user's own requests
        if not request.user.is_staff:
            res = qs.filter(hostingprovider=request.user.hostingprovider)
            return res

        return qs
