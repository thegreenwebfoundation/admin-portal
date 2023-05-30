from django.db import models
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.contrib import admin
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib.auth.admin import UserAdmin, GroupAdmin, Group
import django.forms as dj_forms
from django.utils.safestring import mark_safe
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django import template as dj_template
from guardian.admin import GuardedModelAdmin

from apps.greencheck.admin import (
    GreencheckIpApproveInline,
    GreencheckIpInline,
    GreencheckAsnInline,
    GreencheckAsnApproveInline,
)
from logentry_admin.admin import (
    LogEntry,
    LogEntryAdmin,
    ActionListFilter,
)


from taggit.managers import TaggableManager
from taggit_labels.widgets import LabelWidget

import logging
import markdown

from dal_select2 import views as dal_select2_views

from waffle.models import Flag
from waffle.admin import FlagAdmin

from apps.greencheck.models import GreencheckIpApprove, GreencheckIp
from apps.greencheck.models import GreencheckASNapprove


from apps.greencheck.forms import ImporterCSVForm


from .utils import get_admin_name, reverse_admin_name, send_email
from .admin_site import greenweb_admin
from . import filters
from . import forms
from .forms import (
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
    DataCenterLocation,
    HostingCommunication,
    HostingproviderCertificate,
    Hostingprovider,
    Label,
    HostingProviderNote,
    User,
    DatacenterSupportingDocument,
    HostingProviderSupportingDocument,
    SupportMessage,
    ProviderRequest,
    ProviderRequestASN,
    ProviderRequestIPRange,
    ProviderRequestLocation,
    ProviderRequestEvidence,
    ProviderRequestConsent,
    ProviderRequestStatus,
    Service,
)

logger = logging.getLogger(__name__)


@admin.register(Group, site=greenweb_admin)
class CustomGroupAdmin(GroupAdmin):
    pass


@admin.register(User, site=greenweb_admin)
class CustomUserAdmin(UserAdmin):
    """
    Custom user admin form, with modifications for us by internal
    green web staff members.
    """

    # we override the normal User Creation Form, because we want to support
    # staff members creating users from inside the admin
    add_form = CustomUserCreationForm

    model = User
    search_fields = ("username", "email")
    list_display = ["username", "email", "last_login", "is_staff"]

    # these are not really fields, but a hack to create buttons.
    # see the corresponding methods with the same name
    readonly_fields = ["clear_provider_button"]

    # provide a button to let us clear provider selections easily,
    # as the default select2 widget does not offer this
    @mark_safe
    def clear_provider_button(self, obj):
        return """
            <button
                class='button'
                type='button'
                id='clear-hosting-provider'
                style='padding:0.5rem'
            >
                Clear hosting provider selection
            </button>
        """

    clear_provider_button.short_description = ""

    # make the hosting provider dropdown an autocomplete
    # select2 widget instead
    autocomplete_fields = ("hostingprovider",)

    def get_queryset(self, request, *args, **kwargs):
        """
        This filter the view to only show the current user,
        except if you are internal staff
        """
        qs = super().get_queryset(request, *args, **kwargs)
        if not request.user.is_admin:
            qs = qs.filter(pk=request.user.pk)
        return qs

    def get_fieldsets(self, request, *args, **kwargs):
        """Return different fieldsets depending on the user signed in"""
        # this is the normal username and password combo for
        # creating a user.
        top_row = (None, {"fields": ("username", "password")})

        # followed by the stuff a user might change themselves
        contact_deets = ("Personal info", {"fields": ("email",)})

        # options for setting and clearing the hostingprovider
        # associated with this user
        # TODO: remove or modify this
        hosting_provider = (
            "Linked Hosting Provider",
            {"fields": ("hostingprovider", "clear_provider_button")},
        )

        # what we show for internal staff
        staff_fieldsets = (
            "Permissions",
            {
                "fields": ("is_active", "is_staff", "groups"),
            },
        )

        # our usual set of forms to show for users
        default_fieldset = [top_row, contact_deets]

        # serve the extra staff fieldsets for creating users
        if request.user.is_admin:
            return (*default_fieldset, hosting_provider, staff_fieldsets)

        # allow an override for super users
        if request.user.is_superuser:
            return (
                *default_fieldset,
                hosting_provider,
                staff_fieldsets,
                (
                    "Permissions",
                    {
                        "fields": (
                            "is_active",
                            "is_staff",
                            "is_superuser",
                            "groups",
                        ),
                    },
                ),
            )

        return default_fieldset

    class Media:
        """
        An extended media class, to add an extra snippet
        of js to allow us to clear the select2 dropdown
        """

        js = ("accounts/js/user-change.js",)


class HostingCertificateInline(admin.StackedInline):
    extra = 0
    model = HostingproviderCertificate
    # classes = ["collapse"]


class HostingProviderSupportingDocumentInline(admin.StackedInline):
    extra = 0
    model = HostingProviderSupportingDocument
    form = forms.InlineSupportingDocumentForm


class HostingProviderNoteInline(admin.StackedInline):
    """ """

    extra = 1
    model = HostingProviderNote
    form = HostingProviderNoteForm


class DatacenterNoteInline(admin.StackedInline):
    """
    A inline for adding notes to Datacentres.
    """

    extra = 0
    model = DatacenterNote
    form = DatacenterNoteNoteForm


class DataCenterSupportingDocumentInline(admin.StackedInline):
    extra = 0
    model = DatacenterSupportingDocument


class DataCenterLocationInline(admin.StackedInline):
    extra = 0
    model = DataCenterLocation


@admin.register(Service, site=greenweb_admin)
class ServiceAdmin(admin.ModelAdmin):
    model = Service

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

        if not self.request.user.is_admin:
            return Label.objects.none()

        qs = Label.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


@admin.register(Hostingprovider, site=greenweb_admin)
class HostingAdmin(GuardedModelAdmin):
    form = forms.HostingAdminForm
    list_filter = [
        "archived",
        filters.LabelFilter,
        filters.YearDCFilter,
        filters.YearASNFilter,
        filters.YearIPFilter,
        filters.ShowWebsiteFilter,
        filters.PartnerFilter,
        filters.ServiceFilter,
        filters.CountryFilter,
    ]
    inlines = [
        HostingProviderSupportingDocumentInline,
        GreencheckAsnInline,
        GreencheckIpInline,
        GreencheckAsnApproveInline,
        GreencheckIpApproveInline,
        HostingProviderNoteInline,
    ]
    search_fields = ("name",)

    @admin.display(description="Services offered")
    def service_list(self, obj):
        return [service.name for service in obj.services.all()]

    @admin.display(description="Staff labels")
    def label_list(self, obj):
        return [label.name for label in obj.staff_labels.all()]

    def get_list_display(self, request):
        """
        Change the columns in the list depending on whether
        the user is staff admin of not.
        """

        NON_STAFF_LIST = [
            "name",
            "country_str",
            "html_website",
            "showonwebsite",
            "partner",
            "ip_addresses",
            self.service_list,
        ]

        if request.user.is_admin:
            # staff should be able to see providers,
            # reguardless of whether they were
            # archived or not
            NON_STAFF_LIST.insert(3, "archived")
            return [*NON_STAFF_LIST, self.label_list]

        return NON_STAFF_LIST

    # these are not really fields, but buttons
    # see the corresponding methods
    readonly_fields = ["preview_email_button", "start_csv_import_button"]
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

        user = obj.created_by
        email = None

        if user:
            email = user.email
        if not user:
            messages.add_message(
                request,
                messages.WARNING,
                "No user exists for this host, so you will need to "
                "add an email manually",
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

    def start_import_from_csv(self, request, *args, **kwargs):
        """
        Show the form, and preview required formate for the importer
        for the given hosting provider.
        """

        # get our provider
        provider = Hostingprovider.objects.get(pk=kwargs["provider"])

        # get our document
        data = {"provider": provider.id}
        form = ImporterCSVForm(data)
        form.fields["provider"].widget = dj_forms.widgets.HiddenInput()

        return render(
            request,
            "import_csv_start.html",
            {"form": form, "ip_ranges": [], "provider": provider},
        )

    def save_import_from_csv(self, request, *args, **kwargs):
        """
        Process the contents of the uploaded file, and either
        show a preview of the IP ranges that would be created, or
        create them, based on submitted form value
        """
        provider = Hostingprovider.objects.get(pk=kwargs["provider"])

        if request.method == "POST":
            # get our provider

            # try to get our document
            form = ImporterCSVForm(request.POST, request.FILES)
            form.fields["provider"].widget = dj_forms.widgets.HiddenInput()

            valid = form.is_valid()
            skip_preview = form.cleaned_data["skip_preview"]

            if valid and skip_preview:
                # not doing preview. Run the import
                completed_importer = form.save()

                context = {
                    "ip_ranges": completed_importer,
                    "provider": provider,
                }
                return render(
                    request,
                    "import_csv_results.html",
                    context,
                )

            if valid:
                # the save default we don't save the contents
                # just showing what would happen
                ip_ranges = form.get_ip_ranges()
                context = {
                    "form": form,
                    "ip_ranges": ip_ranges,
                    "provider": provider,
                }
                return render(
                    request,
                    "import_csv_preview.html",
                    context,
                )

            # otherwise fallback to showing the form with errors,
            # ready for another attempted submission

            context = {
                "form": form,
                "ip_ranges": None,
                "provider": provider,
            }

            return render(
                request,
                "import_csv_preview.html",
                context,
            )

        return redirect("greenweb_admin:accounts_hostingprovider_change", provider.id)

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

    # Mutators

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if form.has_changed():
            if not obj.is_awaiting_review and not request.user.is_admin:
                form.instance.label_as_awaiting_review(notify_admins=True)

        # if there is not 'change' set, a user is creating a hosting
        # provider for the first time.
        # Allocate the new provider to them, so they can see their
        # newly created provider on the next page load
        if not change:
            # we don't allocate newly created providers to admin staff
            # they might be creating a provider for someone else
            if not request.user.is_admin:
                user = request.user
                user.hostingprovider = obj
                user.save()

            # and then notify the admins to review the new submission
            if not obj.is_awaiting_review and not request.user.is_admin:
                form.instance.label_as_awaiting_review(notify_admins=True)

    def save_formset(self, request, form, formset, change):
        """
        Save the child objects in this form, and account for the special cases
        for each of the formset being iterated through.

        Called multiple times - once for each formset on a model.
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

            # calling formset.save() lets us see if any of the forms
            # contained in the formset have seen changes like new objects,
            # deleted objects, or changed objects.

            # See more:
            # https://docs.djangoproject.com/en/dev/topics/forms/modelforms/#saving-objects-in-the-formset
            formset.save(commit=False)
            if formset.new_objects:
                for new_obj in formset.new_objects:
                    if isinstance(new_obj, HostingProviderNote):
                        new_obj.added_by = request.user
                        new_obj.save()

        formset.save()

        # check for any changes in the other forms contained in the formset
        changes_in_related_objects = (
            formset.changed_objects or formset.changed_objects or formset.new_objects
        )

        # we don't want to flag the provider for review by internal staff when
        # our internal staff are the ones working on it
        should_flag_for_review = (
            not form.instance.is_awaiting_review and not request.user.is_admin
        )

        if changes_in_related_objects and should_flag_for_review:
            form.instance.label_as_awaiting_review(notify_admins=True)

    def approve_asn(self, request, *args, **kwargs):
        pk = request.GET.get("approval_id")
        action = request.GET.get("action")
        obj = GreencheckASNapprove.objects.get(pk=pk)

        obj.process_approval(action)

        name = "admin:" + get_admin_name(self.model, "change")
        return redirect(name, obj.hostingprovider_id)

    def approve_ip(self, request, *args, **kwargs):
        pk = request.GET.get("approval_id")
        action = request.GET.get("action")
        obj = GreencheckIpApprove.objects.get(pk=pk)

        obj.process_approval(action)

        name = "admin:" + get_admin_name(self.model, "change")
        return redirect(name, obj.hostingprovider_id)

    # Queries

    def get_list_filter(self, request):
        """
        Return a list of filters for admins, otherwise an empty list.


        """
        if request.user.is_admin:
            return super().get_list_filter(request)

        # otherwise return nothing
        return []

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
                "<provider>/start_import_from_csv",
                self.start_import_from_csv,
                name=get_admin_name(self.model, "start_import_from_csv"),
            ),
            path(
                "<provider>/save_import_from_csv",
                self.save_import_from_csv,
                name=get_admin_name(self.model, "save_import_from_csv"),
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
        """
        Returns:
        - for staff users: all hosting providers
        - for regular users: non-archived providers that the user has permissions to
        """
        qs = super().get_queryset(request, *args, **kwargs)
        qs = qs.prefetch_related(
            "hostingprovider_certificates",
            "datacenter",
            "greencheckip_set",
            "services",
        ).annotate(models.Count("greencheckip"))

        if not request.user.is_staff:
            # filter for non-archived providers & those the current user has permissions to
            qs = qs.filter(archived=False).filter(
                id__in=[p.id for p in request.user.hosting_providers]
            )
        return qs

    def get_fieldsets(self, request, obj=None):
        fieldset = [
            (
                "Hostingprovider info",
                {
                    "fields": (
                        ("name", "website", "description"),
                        "country",
                        "city",
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
                    "start_csv_import_button",
                )
            },
        )

        if request.user.is_admin:
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

        logger.info(f"{request.user}, is_admin: {request.user.is_admin}")

        if not request.user.is_admin:
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
        extra_context["bulk_edit_ip_approval_link"] = reverse_admin_name(
            GreencheckIpApprove, "changelist", params={"hostingprovider": object_id}
        )
        extra_context["bulk_edit_ip_range_link"] = reverse_admin_name(
            GreencheckIp, "changelist", params={"hostingprovider": object_id}
        )
        # pass in the extra ip_range_count into our extra context so we can
        # conditionally show a notice when we have too many ip ranges to realistically
        # iterate through
        try:
            instance = self.model.objects.get(id=object_id)
            extra_context["ip_approval_count"] = instance.ip_approval_count
            extra_context["ip_range_count"] = instance.ip_range_count
        except self.model.DoesNotExist:
            logger.warning(f"Could not find provider with the id {object_id}")

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
    def start_csv_import_button(self, obj):
        """
        Create clickable link to begin process of bulk import
        of IP ranges.
        """
        url = reverse_admin_name(
            Hostingprovider,
            name="start_import_from_csv",
            kwargs={"provider": obj.pk},
        )
        link = f'<a href="{url}" class="start_csv_import">Import IP Ranges from CSV</a>'
        return link

    send_button.short_description = "Import IP Ranges from a CSV file"

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
class DatacenterAdmin(GuardedModelAdmin):
    form = forms.DatacenterAdminForm
    inlines = [
        # DatacenterCertificateInline,
        # DatacenterClassificationInline,
        # DatacenterCoolingInline,
        DataCenterSupportingDocumentInline,
        DatacenterNoteInline,
        DataCenterLocationInline,
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
    raw_id_fields = ("created_by",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        """
        Assign the current user to any notes added to a datacenter
        in the current request
        """
        formset.save(commit=False)

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
        # filter for datacenters that the current user has permissions to
        qs = qs.filter(id__in=[p.id for p in request.user.data_centers])
        return qs

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_staff:
            return ["showonwebsite", "created_by"]
        return self.readonly_fields

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (
                "Datacenter info",
                {
                    "fields": (
                        (
                            "name",
                            "website",
                        ),
                        ("country", "created_by"),
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
        ]
        # we only allow green web staff to add hosting providers in the admin
        # to make these changes
        if request.user.is_admin:
            fieldsets.append(
                ("Associated hosting providers", {"fields": ("hostingproviders",)}),
            )
        return fieldsets

    def get_inlines(self, request, obj):
        """
        A dynamic check for inlines so we only show some inlines
        to groups with the correct permissions.
        """
        inlines = self.inlines

        if not request.user.is_admin:
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

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}

        if object_id is not None:
            datacentre = self.model.objects.get(id=object_id)
            associated_providers_count = datacentre.hostingproviders.all().count()

            if associated_providers_count:
                extra_context["associated_providers_count"] = associated_providers_count
                extra_context[
                    "associated_providers"
                ] = datacentre.hostingproviders.all()
                extra_context["dc_has_providers"] = True

        return super().change_view(
            request,
            object_id,
            form_url,
            extra_context=extra_context,
        )

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


greenweb_admin.register(Flag, FlagAdmin)
greenweb_admin.register(LogEntry, GWLogEntryAdmin)


class AdminOnlyTabularInline(admin.TabularInline):
    """
    Specifies a TabularInline admin with all permissions for the admin group
    """

    def has_view_permission(self, request, obj=None):
        return request.user.is_admin

    def has_add_permission(self, request, obj=None):
        return request.user.is_admin

    def has_change_permission(self, request, obj=None):
        return request.user.is_admin


class ProviderRequestASNInline(AdminOnlyTabularInline):
    model = ProviderRequestASN
    extra = 0


class ProviderRequestIPRangeInline(AdminOnlyTabularInline):
    model = ProviderRequestIPRange
    extra = 0


class ProviderRequestEvidenceInline(AdminOnlyTabularInline):
    model = ProviderRequestEvidence
    extra = 0


class ProviderRequestLocationInline(AdminOnlyTabularInline):
    model = ProviderRequestLocation
    extra = 0


class ProviderRequestConsentInline(AdminOnlyTabularInline):
    model = ProviderRequestConsent
    extra = 0
    max_num = 1
    readonly_fields = (
        "data_processing_opt_in",
        "newsletter_opt_in",
    )


class ActionInChangeFormMixin(object):
    """
    Adds custom admin actions
    (https://docs.djangoproject.com/en/4.1/ref/contrib/admin/actions/)
    to the change view of the model.
    """  # noqa: E501

    def response_action(self, request, queryset):
        """
        Prefer HTTP_REFERER for redirect
        """
        response = super(ActionInChangeFormMixin, self).response_action(
            request, queryset
        )
        if isinstance(response, HttpResponseRedirect):
            response["Location"] = request.META.get("HTTP_REFERER", response.url)
        return response

    def change_view(self, request, object_id, extra_context=None):
        """
        Supply custom action form to the admin change_view as a part of context
        """
        actions = self.get_actions(request)
        if actions:
            action_form = self.action_form(auto_id=None)
            action_form.fields["action"].choices = self.get_action_choices(request)
        else:
            action_form = None
        extra_context = extra_context or {}
        extra_context["action_form"] = action_form
        return super(ActionInChangeFormMixin, self).change_view(
            request, object_id, extra_context=extra_context
        )


@admin.register(ProviderRequest, site=greenweb_admin)
class ProviderRequest(ActionInChangeFormMixin, admin.ModelAdmin):
    list_display = ("name", "website", "status", "created")
    inlines = [
        ProviderRequestLocationInline,
        ProviderRequestEvidenceInline,
        ProviderRequestIPRangeInline,
        ProviderRequestASNInline,
        ProviderRequestConsentInline,
    ]
    formfield_overrides = {TaggableManager: {"widget": LabelWidget(model=Service)}}
    empty_value_display = "(empty)"
    list_filter = ("status",)
    readonly_fields = (
        "authorised_by_org",
        "created_by",
        "status",
        "approved_at",
        "location_import_required",
        "network_import_required",
        "missing_network_explanation",
    )
    actions = ["mark_approved", "mark_rejected", "mark_removed"]
    change_form_template = "admin/provider_request/change_form.html"

    def send_approval_email(self, provider_request, request):
        """
        Send an email to the provider whose request was approved by staff.
        """

        provider_url = provider_request.hostingprovider_set.first().admin_url
        context = {
            "username": provider_request.created_by.username,
            "org_name": provider_request.name,
            "update_url": request.build_absolute_uri(provider_url),
        }

        # inject additional info to providers with multiple locations

        # TODO: when multiple locations on Hostingprovider are implemented,
        # change the code below + template logic
        locations = provider_request.providerrequestlocation_set.all()
        if len(locations) > 1:
            location_context = {
                "locations": ", ".join(
                    f"{location.city} ({location.country.name})"
                    for location in locations
                ),
                "first_location": f"{locations.first().city}, {locations.first().country.name}",
            }
            context.update(location_context)

        send_email(
            address=provider_request.created_by.email,
            subject="Approval of your verification request for the Green Web database",
            context=context,
            template_txt="emails/verification_request_approved.txt",
            template_html="emails/verification_request_approved.html",
        )

    @admin.action(description="Approve", permissions=["change"])
    def mark_approved(self, request, queryset):
        for provider_request in queryset:
            try:
                hp = provider_request.approve()
                hp_href = reverse(
                    "greenweb_admin:accounts_hostingprovider_change", args=[hp.id]
                )
                message = mark_safe(
                    f"""
                    Successfully approved the request '{provider_request}'.
                    Created a Hosting provider: <a href={hp_href}>'{hp}'</a>
                    """
                )
                self.message_user(request, message=message, level=messages.SUCCESS)
                self.send_approval_email(provider_request, request)

            except Exception as e:
                message = mark_safe(
                    f"""
                    Failed to approve the request '{provider_request}'.<br><br>
                    Detailed error:<br>{e}
                    """
                )
                self.message_user(request, message=message, level=messages.ERROR)

    @admin.action(description="Reject", permissions=["change"])
    def mark_rejected(self, request, queryset):
        for provider_request in queryset:
            provider_request.status = ProviderRequestStatus.REJECTED.value
            provider_request.save()

            message = mark_safe(
                f"""
                    Request id <em>{provider_request.id}</em> for provider: \
                    <em>{provider_request.name}</em> has been rejected.
                    They creator of this request has <em>not</em> been contacted yet -
                    you will need to contact them if appropriate.
                    """
            )
            self.message_user(request, message=message, level=messages.SUCCESS)

    @admin.action(description="Remove", permissions=["change"])
    def mark_removed(self, request, queryset):
        """
        Mark the selected verification a 'removed', and remove it from the
        dashboard for a given user. Used when we do not want to delete data,
        but it doesn't make sense to have the request lingering in a user's
        dashboard either.
        """
        for provider_request in queryset:
            provider_request.status = ProviderRequestStatus.REMOVED.value
            provider_request.save()

            message = mark_safe(
                f"""
                    Request id <em>{provider_request.id}</em> for provider: \
                    <em>{provider_request.name}</em> has been removed.
                    The request has not been deleted, but will not show up in a user's
                    provider portal view.
                    The creator of this request has <em>not</em> been contacted yet - you
                    will need to contact them if appropriate.
                    """
            )
            self.message_user(request, message=message, level=messages.SUCCESS)
