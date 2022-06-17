from django.db import models
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.contrib import admin
from django.urls import reverse
from django.contrib.auth.admin import UserAdmin, GroupAdmin, Group
from django.utils.safestring import mark_safe
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django import template as dj_template
from apps.greencheck.admin import (
    GreencheckASNApprove,
    GreencheckIpApproveInline,
    GreencheckIpInline,
    GreencheckAsnInline,
    GreencheckAsnApproveInline,
)
from taggit.models import Tag
import logging
import markdown

from dal_select2 import views as dal_select2_views

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
from .forms import (
    CustomUserChangeForm,
    CustomUserCreationForm,
    HostingProviderNoteForm,
    DatacenterNoteNoteForm,
)
from .models import (
    Datacenter,
    DatacenterCertificate,
    DatacenterClassification,
    DatacenterCooling,
    DatacenterNote,
    HostingCommunication,
    HostingproviderCertificate,
    Hostingprovider,
    Label,
    ProviderLabel,
    HostingProviderNote,
    User,
    DatacenterSupportingDocument,
    HostingProviderSupportingDocument,
    SupportMessage,
)

logger = logging.getLogger(__name__)


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
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2"),
            },
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


class HostingProviderNoteInline(admin.StackedInline):
    """ """

    extra = 1
    model = HostingProviderNote
    form = HostingProviderNoteForm


class DatacenterNoteInline(admin.StackedInline):
    """
    A data
    """

    extra = 0
    model = DatacenterNote
    form = DatacenterNoteNoteForm


class DataCenterSupportingDocumentInline(admin.StackedInline):
    extra = 0
    model = DatacenterSupportingDocument


@admin.register(Tag, site=greenweb_admin)
class ServiceAdmin(admin.ModelAdmin):
    model = Tag

    class Meta:
        verbose_name = "Services Offered"


@admin.register(Label, site=greenweb_admin)
class LabelAdmin(admin.ModelAdmin):
    model = Label

    class Meta:
        verbose_name = "Provider Label"


class LabelAutocompleteView(dal_select2_views.Select2QuerySetView):
    def get_queryset(self):
        """
        Return our list of labels, only serving them to internal staff members"""

        if not self.request.user.groups.filter(name="admin").exists():
            return Label.objects.none()

        qs = Label.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


@admin.register(Hostingprovider, site=greenweb_admin)
class HostingAdmin(admin.ModelAdmin):
    form = forms.HostingAdminForm
    list_filter = [
        filters.LabelFilter,
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
        HostingProviderNoteInline,
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
        "services",
    ]
    # these are not really fields, but buttons
    # see the corresponding methods
    readonly_fields = ["preview_email_button"]
    ordering = ("name",)

    # Factories

    def preview_email(self, request, *args, **kwargs):
        """
        Create and preview a sample email asking for further information
        from a hosting provider to support their claims.
        """

        # workout which email template to start with
        email_name = request.GET.get("email")

        obj = Hostingprovider.objects.get(pk=kwargs["provider"])

        support_message = SupportMessage.objects.get(pk=email_name)
        message_type = support_message.category
        message_body_template = dj_template.Template(support_message.body)
        message_subject_template = dj_template.Template(support_message.subject)

        user = obj.user_set.all().first()
        email = None

        if user:
            email = user.email
        if not user:
            messages.add_message(
                request,
                messages.WARNING,
                (
                    "No user exists for this host, so you will need to "
                    "add an email manually"
                ),
            )

        context = dj_template.Context({"host": obj, "recipient": user})

        rendered_subject: str = message_subject_template.render(context)
        rendered_message: str = message_body_template.render(context)

        cancel_link = reverse(
            "admin:" + get_admin_name(self.model, "change"), args=[obj.pk]
        )

        send_email_path = f"greenweb_admin:{get_admin_name(self.model, 'send_email')}"
        send_email_url = reverse(send_email_path, args=[obj.id])
        logger.info(f"send_email_url - {send_email_url}")

        prepopulated_form = forms.PreviewEmailForm(
            initial={
                "recipient": email or None,
                "title": rendered_subject,
                "body": rendered_message,
                "message_type": message_type,
                "provider": obj.id,
            }
        )

        context = {
            "form": prepopulated_form,
            "form_url": send_email_url,
            "cancel_link": cancel_link,
        }

        return render(request, "preview_email.html", context)

    def send_email(self, request, *args, **kwargs):
        """
        Send the given email, log the outbound request in the admin, and
        then tag with email sent
        """

        subject = request.POST.get("title")
        recipients = request.POST.get("recipient").split(",")
        message = request.POST.get("body")
        message_mkdn = markdown.markdown(message)
        message_type = request.POST.get("message_type")
        provider_id = request.POST.get("provider")
        obj = Hostingprovider.objects.get(pk=provider_id)

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipients,
            html_message=message_mkdn,
        )

        messages.add_message(request, messages.INFO, "Email sent to user")

        # add hosting provider note, so we have a record of
        # sending the request

        HostingProviderNote.objects.create(
            added_by=request.user, body_text=message, provider=obj
        )

        # TODO: is this needed any more?
        # make note of the outbound message we sent
        HostingCommunication.objects.create(
            template=message_type, hostingprovider=obj, message_content=message
        )
        # add our internal label, so we know when they were last contacted
        # and we don't keep sending requests
        obj.staff_labels.add(f"{message_type} sent")

        # add a tag to the hosting provider so we know they were messaged

        name = "admin:" + get_admin_name(self.model, "change")
        return redirect(name, obj.pk)

    def inform_updated_supporting_evidence(self, hosting_provider):
        label_text = f"supporting-evidence-validation-pending"

        # Return if action has already been taken to inform
        if label_text in hosting_provider.staff_labels.names():
            logger.info(f"label {label_text} already applied")
            return

        # Add label to the form to indicate that it is ready for evaluation
        hosting_provider.staff_labels.add(label_text)

        # Send mail to update staff about a pending evaluation
        email_message = render_to_string(
            "emails/request_evaluation_supporting_evidence_email.txt",
            context={
                "user_name": "PLACEHOLDER_NAME", # TODO: put name of the user in
                "overview_link": "PLACEHOLDER_LINK", # TODO: needs to refer to the overiew with the applied filter of this tag (/admin/accounts/hostingprovider/?label=supporting-evidence-validation-pending)
            },
        )
        # TODO: make sure the "to" and "from" addresses are correct
        send_mail(
            "Evaluation request regarding updated supporting evidence",
            email_message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.DEFAULT_FROM_EMAIL],
            fail_silently=False,
        )

    # Mutators

    def save_model(self, request, obj, form, change):

        super().save_model(request, obj, form, change)

        if not change:
            user = request.user
            user.hostingprovider = obj
            user.save()

    def save_formset(self, request, form, formset, change):
        """
        Save the child objects in this form, and account for the special cases
        for each of the formset being iterated through.

        Called multiple times - once for each formset on an model.
        """

        # We need to let the form know if this an addition or a change
        # so that approval record is saved correctly in case of a
        # non-staff user.

        # We set the 'changed' property on the formset form, so that our
        # ApprovalMixin._save_approval()_can pick up whether a change
        # # has taken place.
        formset.form.changed = change

        if formset.form.__name__ == "HostingProviderNoteForm":
            # assign the current user to the
            # newly created comments
            instances = formset.save(commit=False)
            if formset.new_objects:
                for new_obj in formset.new_objects:
                    if isinstance(new_obj, HostingProviderNote):
                        new_obj.added_by = request.user
                        new_obj.save()
        elif formset.form.__name__ == "HostingProviderSupportingDocumentForm":
            logger.info("found HostingProviderSupportingDocumentForm")
            # TODO: by Chris: check if there is any update compared to the old version
            # if yes, execute the following function:
            # self.inform_updated_supporting_evidence(hosting_provider)

        formset.save()

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

    # Queries

    def get_urls(self):
        """
        Define the urls for extra functionality related to operations on
        this hosting provider
        """
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
                "<provider>/send_email",
                self.send_email,
                name=get_admin_name(self.model, "send_email"),
            ),
            path(
                "<provider>/preview_email",
                self.preview_email,
                name=get_admin_name(self.model, "preview_email"),
            ),
        ]
        # order is important !!
        return added + urls

    def get_queryset(self, request, *args, **kwargs):
        qs = super().get_queryset(request, *args, **kwargs)
        if "archived" not in request.GET:
            qs = qs.filter(archived=False)

        qs = qs.prefetch_related(
            "hostingprovider_certificates",
            "datacenter",
            "greencheckip_set",
            "services",
        ).annotate(models.Count("greencheckip"))
        if not request.user.is_staff:
            qs = qs.filter(user=request.user)
        return qs

    def get_fieldsets(self, request, obj=None):
        fieldset = [
            (
                "Hostingprovider info",
                {
                    "fields": (
                        (
                            "name",
                            "website",
                        ),
                        "country",
                        "services",
                    )
                },
            )
        ]

        admin_editable = (
            "Admin only",
            {
                "fields": (
                    (
                        "archived",
                        "showonwebsite",
                        "customer",
                    ),
                    ("partner", "model"),
                    ("staff_labels",),
                    ("email_template", "preview_email_button"),
                )
            },
        )
        if request.user.is_staff:
            fieldset.append(admin_editable)
        return fieldset

    # Properties

    def services(self, obj):
        return ", ".join(o.name for o in obj.services.all())

    def get_readonly_fields(self, request, obj=None):
        read_only = super().get_readonly_fields(request, obj)
        if not request.user.is_staff:
            return read_only + ["partner"]
        return read_only

    def get_inlines(self, request, obj):
        """
        A dynamic check for inlines so we only show some inlines
        to groups with the correct permissions.
        """
        inlines = self.inlines
        is_admin = request.user.groups.filter(name="admin").exists()

        logger.info(f"{request.user}, is_admin: {is_admin}")

        if not is_admin:
            # they're not an admin, return a
            # from the list filtered to remove the 'admin'
            # inlines.
            # We return a filtered list, because changing the state of
            # `inlines` sometimes returns a list to admin users with the
            # admin inlines removed.
            admin_inlines = (
                # GreencheckAsnApproveInline,
                # GreencheckIpApproveInline,
                HostingProviderNoteInline,
            )
            filtered_inlines = []
            for inline in inlines:
                if inline not in admin_inlines:
                    filtered_inlines.append(inline)
            return filtered_inlines

        return inlines

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
    def send_button(self, obj):
        url = reverse_admin_name(
            Hostingprovider,
            name="send_email",
            kwargs={"provider": obj.pk},
        )
        link = f'<a href="{url}" class="sendEmail">Send email</a>'
        return link

    send_button.short_description = "Send email"

    @mark_safe
    def preview_email_button(self, obj):
        url = reverse_admin_name(
            Hostingprovider,
            name="preview_email",
            kwargs={"provider": obj.pk},
        )
        link = f'<a href="{url}" class="sendEmail">Compose message</a>'
        return link

    preview_email_button.short_description = "Support Messages"

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
        DatacenterNoteInline,
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

    def save_formset(self, request, form, formset, change):
        """
        Assign the current user to any notes added to a datacenter
        in the current request
        """
        instances = formset.save(commit=False)

        if formset.new_objects:
            for new_obj in formset.new_objects:
                if isinstance(new_obj, DatacenterNote):
                    new_obj.added_by = request.user
                    new_obj.save()

        formset.save()

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
                        (
                            "name",
                            "website",
                        ),
                        ("country", "user"),
                        ("pue", "residualheat"),
                        (
                            "temperature",
                            "temperature_type",
                        ),
                        ("dc12v", "virtual", "greengrid", "showonwebsite"),
                        ("model",),
                    ),
                },
            ),
            (None, {"fields": ("hostingproviders",)}),
        ]
        return fieldset

    def get_inlines(self, request, obj):
        """
        A dynamic check for inlines so we only show some inlines
        to groups with the correct permissions.
        """
        inlines = self.inlines
        is_admin = request.user.groups.filter(name="admin").exists()

        logger.info(f"{request.user}, is_admin: {is_admin}")

        if not is_admin:
            # they're not an admin, return a
            # from the list filtered to remove the 'admin'
            # inlines.
            # We return a filtered list, because changing the state of
            # `inlines` sometimes returns a list to admin users with the
            # admin inlines removed.
            admin_inlines = (DatacenterNoteInline,)
            filtered_inlines = []
            for inline in inlines:
                if inline not in admin_inlines:
                    filtered_inlines.append(inline)
            return filtered_inlines

        return inlines

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


@admin.register(SupportMessage, site=greenweb_admin)
class SupportMessageAdmin(admin.ModelAdmin):

    # only staff should see this
    pass


greenweb_admin.register(Flag, FlagAdmin)
