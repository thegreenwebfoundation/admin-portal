import logging
import django.forms as dj_forms
import markdown
from django import template as dj_template
from django.conf import settings
from django.contrib import admin, messages
from django.core.mail import send_mail
from django.db import models
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.safestring import mark_safe

from apps.greencheck.admin import (
    GreencheckAsnApproveInline,
    GreencheckAsnInline,
    GreencheckIpApproveInline,
    GreencheckIpInline,
)
from apps.greencheck.forms import ImporterCSVForm
from apps.greencheck.models import (
    GreencheckASNapprove,
    GreencheckIp,
    GreencheckIpApprove,
)

from ... import filters, forms
from ...admin_site import greenweb_admin
from ...forms import (
    HostingProviderNoteForm,
)
from ...models import (
    HostingCommunication,
    Hostingprovider,
    HostingproviderCertificate,
    HostingProviderNote,
    HostingProviderSupportingDocument,
    Label,
    LinkedDomain,
    Service,
    SupportMessage,
    VerificationBasis,
)
from ...utils import get_admin_name, reverse_admin_name
from ..abstract import ObjectPermissionsAdminMixin

logger = logging.getLogger(__name__)

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


@admin.register(Service, site=greenweb_admin)
class ServiceAdmin(admin.ModelAdmin):
    model = Service

    class Meta:
        verbose_name = "Services Offered"

@admin.register(VerificationBasis, site=greenweb_admin)
class VerificationBasisAdmin(admin.ModelAdmin):
    model = VerificationBasis

    class Meta:
        verbose_name = "Bases for Verification"


@admin.register(Label, site=greenweb_admin)
class LabelAdmin(admin.ModelAdmin):
    model = Label

    class Meta:
        verbose_name = "Provider Label"

@admin.register(LinkedDomain, site=greenweb_admin)
class LinkedDomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "state", "provider", "is_primary", "active",  "created")
    search_fields = ("domain", "provider__name", "state")
    ordering = ("domain", "provider__name", "state", "is_primary", "active", "created")


@admin.register(SupportMessage, site=greenweb_admin)
class SupportMessageAdmin(admin.ModelAdmin):
    # only staff should see this
    pass

@admin.register(Hostingprovider, site=greenweb_admin)
class HostingAdmin(
    ObjectPermissionsAdminMixin,
    admin.ModelAdmin,
):
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
        GreencheckIpInline,
        GreencheckIpApproveInline,
        GreencheckAsnInline,
        GreencheckAsnApproveInline,
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
            "is_listed",
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

    readonly_fields = [
        "authorised_users",
        "data_centers",
        "preview_email_button",
        "start_csv_import_button",
    ]
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
        """
        Extra actions in response to specific options being set on the main model go here.
        Note: this will not catch changes made to inlines. For that see the overrides in
        the save_formset()

        https://docs.djangoproject.com/en/dev/ref/contrib/admin/#django.contrib.admin.ModelAdmin.save_model
        """

        # if the provider is being archived, deactivate all networks to avoid having
        # to manually do this for each network
        if "archived" in form.changed_data and form.instance.archived:
            form.instance.archive()

        super().save_model(request, obj, form, change)

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
            "verification_bases",
        ).annotate(models.Count("greencheckip"))

        if not request.user.is_admin:
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
                        "name",
                        "website",
                        "description",
                        "country",
                        "city",
                        "services",
                        "verification_bases",
                        "created_by",
                    )
                },
            ),
        ]

        users_fieldset = (
            "Authorised hosting provider users",
            {"fields": ("authorised_users",)},
        )
        dc_fieldset = (
            "Associated datacenters",
            {"fields": ("data_centers",)},
        )
        if obj is not None:
            fieldset.extend([users_fieldset, dc_fieldset])

        admin_editable = (
            "Admin only",
            {
                "fields": (
                    (
                        "archived",
                        "is_listed",
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

    @mark_safe
    def authorised_users(self, obj):
        """
        Returns markup for a list of all users with *explicit* permissions to manage the Hostingprovider
        """
        if not obj.users_explicit_perms:
            return "No external users found! Only administrators are authorised"
        return "<br>".join(
            [
                f"<a href={u.admin_url}>{u.username}</a>"
                for u in obj.users_explicit_perms
            ]
        )

    @mark_safe
    def data_centers(self, obj):
        """
        Returns a markup for a list of associated data centers
        """
        dcs = obj.datacenter.all()
        if not dcs:
            return "There are no data centres associated with this hosting provider."
        return "<br>".join([f"<a href={dc.admin_url}>{dc.name}</a>" for dc in dcs])

    def services(self, obj):
        return ", ".join(o.name for o in obj.services.all())

    def get_readonly_fields(self, request, obj=None):
        read_only = super().get_readonly_fields(request, obj)
        if not request.user.is_admin:
            read_only.append("partner")
        if obj is not None:
            read_only.append("created_by")
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

        # when we have too many IPs to realistically show on the page
        # we top trying to show the GreencheckIPs inline, and instead
        # use a link to the relvevant change list in the template.
        # see admin/accounts/hostingprovider/change_form.html
        if obj and obj.ip_range_count > 500:
            if GreencheckIpInline in inlines:
                inlines.remove(GreencheckIpInline)

        return inlines

    def _changeform_view(self, request, object_id, form_url, extra_context):
        """Include whether current user is staff, so it can be picked up by a form"""
        # TODO: clarify why the "is_staff" flag is passed to the form
        # and until then, use the value from is_admin
        if request.method == "POST":
            post = request.POST.copy()
            post["is_staff"] = request.user.is_admin
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

    @admin.display(
        description="Send email"
    )
    @admin.display(
        description="Import IP Ranges from a CSV file"
    )
    @mark_safe
    def send_button(self, obj):
        url = reverse_admin_name(
            Hostingprovider,
            name="send_email",
            kwargs={"provider": obj.pk},
        )
        link = f'<a href="{url}" class="sendEmail">Send email</a>'
        return link


    @admin.display(
        description="Support Messages"
    )
    @mark_safe
    def preview_email_button(self, obj):
        url = reverse_admin_name(
            Hostingprovider,
            name="preview_email",
            kwargs={"provider": obj.pk},
        )
        link = f'<a href="{url}" class="sendEmail">Compose message</a>'
        return link


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


    @admin.display(
        description="website"
    )
    @mark_safe
    def html_website(self, obj):
        html = f'<a href="{obj.website}" target="_blank">{obj.website}</a>'
        return html


    @admin.display(
        description="Number of IP ranges",
        ordering="greencheckip__count",
    )
    def ip_addresses(self, obj):
        return len(obj.greencheckip_set.all())


    @admin.display(
        description="country"
    )
    def country_str(self, obj):
        return obj.country.code


    @admin.display(
        description="Certificates"
    )
    def certificates_amount(self, obj):
        return len(obj.hostingprovider_certificates.all())

    # certificates_amount.admin_order_field = "hostingprovider_certificates__count"

    @admin.display(
        description="Datacenters"
    )
    def datacenter_amount(self, obj):
        return len(obj.datacenter.all())

    # datacenter_amount.admin_order_field = "datacenter__count"
