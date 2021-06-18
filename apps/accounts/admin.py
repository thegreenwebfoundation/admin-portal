from django.db import models
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin, Group
from django.utils.safestring import mark_safe
from django.shortcuts import redirect
from django.template.loader import render_to_string
from apps.greencheck.admin import (
    GreencheckASNApprove,
    GreencheckIpApproveInline,
    GreencheckIpInline,
    GreencheckAsnInline,
    GreencheckAsnApproveInline,
)
from taggit.models import Tag

from waffle.models import Flag
from waffle.admin import FlagAdmin

from apps.greencheck.models import GreencheckASN
from apps.greencheck.models import GreencheckIp
from apps.greencheck.models import GreencheckIpApprove
from apps.greencheck.models import GreencheckASNapprove
from apps.greencheck.choices import StatusApproval

from .utils import get_admin_name, reverse_admin_name
from .admin_site import greenweb_admin
from . import filters
from . import forms
from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import (
    Datacenter,
    DatacenterCertificate,
    DatacenterClassification,
    DatacenterCooling,
    HostingCommunication,
    HostingproviderCertificate,
    Hostingprovider,
    User,
    DatacenterSupportingDocument,
    HostingProviderSupportingDocument,
)


@admin.register(Group, site=greenweb_admin)
class CustomGroupAdmin(GroupAdmin):
    pass


@admin.register(User, site=greenweb_admin)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    search_fields = ("username", "email")
    list_display = ["username", "email", "last_login", "is_staff"]

    add_fieldsets = (
        (
            None,
            {"classes": ("wide",), "fields": ("username", "password1", "password2"),},
        ),
    )

    def get_queryset(self, request, *args, **kwargs):
        qs = super().get_queryset(request, *args, **kwargs)
        if not request.user.is_staff:
            qs = qs.filter(pk=request.user.pk)
        return qs

    def get_fieldsets(self, request, *args, **kwargs):

        if request.user.is_superuser:
            return (
                (None, {"fields": ("username", "password")}),
                ("Personal info", {"fields": ("email",)}),
                (
                    "Permissions",
                    {
                        "fields": (
                            "is_active",
                            "is_staff",
                            "is_superuser",
                            "groups",
                            "user_permissions",
                        ),
                    },
                ),
                ("Important dates", {"fields": ("last_login", "date_joined")}),
            )
        # TODO DRY this up, once the security hole is plugged

        return (
            (None, {"fields": ("username", "password")}),
            ("Personal info", {"fields": ("email",)}),
            ("Important dates", {"fields": ("last_login", "date_joined")}),
        )


class HostingCertificateInline(admin.StackedInline):
    extra = 0
    model = HostingproviderCertificate
    # classes = ["collapse"]


class HostingProviderSupportingDocumentInline(admin.StackedInline):
    extra = 0
    model = HostingProviderSupportingDocument


class DataCenterSupportingDocumentInline(admin.StackedInline):
    extra = 0
    model = DatacenterSupportingDocument


@admin.register(Tag, site=greenweb_admin)
class ServiceAdmin(admin.ModelAdmin):
    model = Tag

    class Meta:
        verbose_name = "Services Offered"


@admin.register(Hostingprovider, site=greenweb_admin)
class HostingAdmin(admin.ModelAdmin):
    form = forms.HostingAdminForm
    list_filter = [
        filters.YearDCFilter,
        filters.YearASNFilter,
        filters.YearIPFilter,
        filters.ShowWebsiteFilter,
        filters.PartnerFilter,
        filters.CountryFilter,
    ]
    inlines = [
        # HostingCertificateInline,
        HostingProviderSupportingDocumentInline,
        GreencheckAsnInline,
        GreencheckIpInline,
        GreencheckAsnApproveInline,
        GreencheckIpApproveInline,
    ]
    search_fields = ("name",)
    list_display = [
        "name",
        "country_str",
        "html_website",
        "showonwebsite",
        "partner",
        "model",
        "certificates_amount",
        "datacenter_amount",
        "ip_addresses",
    ]
    readonly_fields = ["send_button"]
    ordering = ("name",)

    def get_queryset(self, request, *args, **kwargs):
        qs = super().get_queryset(request, *args, **kwargs)
        qs = qs.prefetch_related(
            "hostingprovider_certificates", "datacenter", "greencheckip_set"
        ).annotate(models.Count("greencheckip"))
        if not request.user.is_staff:
            qs = qs.filter(user=request.user)
        return qs

    def get_fieldsets(self, request, obj=None):
        fieldset = [
            (
                "Hostingprovider info",
                {"fields": (("name", "website",), "country", "services")},
            )
        ]

        admin_editable = (
            "Admin only",
            {
                "fields": (
                    ("archived", "showonwebsite", "customer",),
                    ("partner", "model"),
                    ("email_template", "send_button"),
                )
            },
        )
        if request.user.is_staff:
            fieldset.append(admin_editable)
        return fieldset

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            user = request.user
            user.hostingprovider = obj
            user.save()

    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()
        added = [
            path(
                "approval_asn/",
                self.approve_asn,
                name=get_admin_name(self.model, "approval_asn"),
            ),
            path(
                "approval_ip/",
                self.approve_ip,
                name=get_admin_name(self.model, "approval_ip"),
            ),
            path(
                "send_email/<provider>/",
                self.send_email,
                name=get_admin_name(self.model, "send_email"),
            ),
        ]
        # order is important !!
        return added + urls

    @mark_safe
    def send_button(self, obj):
        url = reverse_admin_name(
            Hostingprovider, name="send_email", kwargs={"provider": obj.pk},
        )
        link = f'<a href="{url}" class="sendEmail">Send email</a>'
        return link

    send_button.short_description = "Send email"

    def send_email(self, request, *args, **kwargs):
        email_name = request.GET.get("email")
        email_template = f"emails/{email_name}"
        redirect_name = "admin:" + get_admin_name(self.model, "change")

        obj = Hostingprovider.objects.get(pk=kwargs["provider"])
        subject = {
            "additional-info.txt": (
                "Additional information needed to approve "
                "your listing in the Green Web Directory."
            ),
            "pending-removal.txt": (
                "Pending removal from the Green Web Directory due "
                f"to questions around the green hosting of {obj.name}"
            ),
        }
        user = obj.user_set.all().first()
        if not user:
            messages.add_message(
                request,
                messages.WARNING,
                "No user exists for this host, so no email was sent",
            )
            return redirect(redirect_name, obj.pk)
        context = {
            "host": obj,
            "user": user,
        }
        message = render_to_string(email_template, context=context)
        send_mail(
            subject[email_name], message, settings.DEFAULT_FROM_EMAIL, [user.email]
        )

        messages.add_message(request, messages.INFO, "Email sent to user")

        HostingCommunication.objects.create(
            template=email_template, hostingprovider=obj
        )

        name = "admin:" + get_admin_name(self.model, "change")
        return redirect(name, obj.pk)

    def approve_asn(self, request, *args, **kwargs):

        pk = request.GET.get("approval_id")
        action = request.GET.get("action")
        obj = GreencheckASNapprove.objects.get(pk=pk)

        approved_asn = obj.process_approval(action)

        name = "admin:" + get_admin_name(self.model, "change")
        return redirect(name, obj.hostingprovider_id)

    def approve_ip(self, request, *args, **kwargs):
        pk = request.GET.get("approval_id")
        action = request.GET.get("action")
        obj = GreencheckIpApprove.objects.get(pk=pk)

        approved_ip_range = obj.process_approval(action)

        name = "admin:" + get_admin_name(self.model, "change")
        return redirect(name, obj.hostingprovider_id)

    def save_formset(self, request, form, formset, change):
        """
        We need to let the form know if this an addition or a change
        so that approval record is saved correctly in case of a
        non-staff user.
        """

        # A bit of a hack, we need to let the form know that it has changed
        # somehow, this was the easiest way of doing it.
        formset.form.changed = change
        formset.save()

    def get_readonly_fields(self, request, obj=None):
        read_only = super().get_readonly_fields(request, obj)
        if not request.user.is_staff:
            return read_only + ["partner"]
        return read_only

    def _changeform_view(self, request, object_id, form_url, extra_context):
        """Include whether current user is staff, so it can be picked up by a form"""
        if request.method == "POST":
            post = request.POST.copy()
            post["is_staff"] = request.user.is_staff
            request.POST = post

        extra_context = extra_context or {}
        extra_context["bulk_edit_link"] = reverse_admin_name(
            GreencheckIpApprove, "changelist", params={"hostingprovider": object_id}
        )
        return super()._changeform_view(request, object_id, form_url, extra_context)

    @mark_safe
    def html_website(self, obj):
        html = f'<a href="{obj.website}" target="_blank">{obj.website}</a>'
        return html

    html_website.short_description = "website"

    def ip_addresses(self, obj):
        return len(obj.greencheckip_set.all())

    ip_addresses.short_description = "Number of IP ranges"
    ip_addresses.admin_order_field = "greencheckip__count"

    def country_str(self, obj):
        return obj.country.code

    country_str.short_description = "country"

    def certificates_amount(self, obj):
        return len(obj.hostingprovider_certificates.all())

    certificates_amount.short_description = "Certificates"
    # certificates_amount.admin_order_field = "hostingprovider_certificates__count"

    def datacenter_amount(self, obj):
        return len(obj.datacenter.all())

    datacenter_amount.short_description = "Datacenters"
    # datacenter_amount.admin_order_field = "datacenter__count"


class DatacenterCertificateInline(admin.TabularInline):
    extra = 0
    model = DatacenterCertificate
    classes = ["collapse"]

    # def get_formset(self, request, obj=None, **kwargs):
    # give kwargs a dictionary of widgets to change widgets.


class DatacenterClassificationInline(admin.TabularInline):
    extra = 0
    model = DatacenterClassification
    classes = ["collapse"]


class DatacenterCoolingInline(admin.TabularInline):
    extra = 0
    model = DatacenterCooling
    classes = ["collapse"]


@admin.register(Datacenter, site=greenweb_admin)
class DatacenterAdmin(admin.ModelAdmin):
    form = forms.DatacenterAdminForm
    inlines = [
        # DatacenterCertificateInline,
        # DatacenterClassificationInline,
        # DatacenterCoolingInline,
        DataCenterSupportingDocumentInline,
    ]
    search_fields = ("name",)

    list_display = [
        "name",
        "html_website",
        "country_str",
        "model",
        "pue",
        "classification_names",
        "show_website",
        "certificates_amount",
        "hostingproviders_amount",
    ]
    ordering = ("name",)
    raw_id_fields = ("user",)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request, *args, **kwargs):
        qs = super().get_queryset(request, *args, **kwargs)
        qs = qs.prefetch_related(
            "classifications", "datacenter_certificates", "hostingproviders"
        )
        return qs

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_staff:
            return ["showonwebsite", "user"]
        return self.readonly_fields

    def get_fieldsets(self, request, obj=None):
        fieldset = [
            (
                "Datacenter info",
                {
                    "fields": (
                        ("name", "website",),
                        ("country", "user"),
                        ("pue", "residualheat"),
                        ("temperature", "temperature_type",),
                        ("dc12v", "virtual", "greengrid", "showonwebsite"),
                        ("model",),
                    ),
                },
            ),
            (None, {"fields": ("hostingproviders",)}),
        ]
        return fieldset

    @mark_safe
    def html_website(self, obj):
        html = f'<a href="{obj.website}" target="_blank">{obj.website}</a>'
        return html

    html_website.short_description = "website"

    def country_str(self, obj):
        return obj.country.code

    country_str.short_description = "country"

    def show_website(self, obj):
        return obj.showonwebsite

    show_website.short_description = "Show on website"
    show_website.boolean = True

    def classification_names(self, obj):
        classifications = [c.classification for c in obj.classifications.all()]
        return ", ".join(classifications)

    classification_names.short_description = "Classifications"

    def certificates_amount(self, obj):
        return len(obj.datacenter_certificates.all())

    certificates_amount.short_description = "Certificates"

    def hostingproviders_amount(self, obj):
        return len(obj.hostingproviders.all())

    hostingproviders_amount.short_description = "Hosters"


greenweb_admin.register(Flag, FlagAdmin)
