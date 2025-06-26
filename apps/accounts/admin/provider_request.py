import typing

from django.contrib import admin, messages
from django.contrib.admin.models import CHANGE
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.urls import reverse
from django.utils.safestring import mark_safe
from logentry_admin.admin import (
    LogEntry,
)
from taggit_labels.widgets import LabelWidget

from ..admin_site import greenweb_admin
from ..models import (
    Hostingprovider,
    ProviderRequest,
    ProviderRequestASN,
    ProviderRequestEvidence,
    ProviderRequestIPRange,
    ProviderRequestLocation,
    ProviderRequestStatus,
    Service,
    VerificationBasis,
)
from ..utils import send_email
from .abstract import ActionInChangeFormMixin, AdminOnlyTabularInline


class ProviderRequestASNInline(AdminOnlyTabularInline):
    model = ProviderRequestASN
    extra = 0


class ProviderRequestIPRangeInline(AdminOnlyTabularInline):
    model = ProviderRequestIPRange
    extra = 0

    readonly_fields = ["ip_range_size"]
    fields = ["start", "end", "ip_range_size"]


class ProviderRequestEvidenceInline(AdminOnlyTabularInline):
    model = ProviderRequestEvidence
    extra = 0


class ProviderRequestLocationInline(AdminOnlyTabularInline):
    model = ProviderRequestLocation
    extra = 0

@admin.register(ProviderRequest, site=greenweb_admin)
class ProviderRequest(ActionInChangeFormMixin, admin.ModelAdmin):
    list_display = ("name", "website", "status", "created")
    inlines = [
        ProviderRequestLocationInline,
        ProviderRequestEvidenceInline,
        ProviderRequestIPRangeInline,
        ProviderRequestASNInline,
    ]
    search_fields = ("name", "website")
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
        "newsletter_opt_in",
        "data_processing_opt_in",
        "provider",
    )
    actions = ["mark_approved", "mark_open", "mark_rejected", "mark_removed"]
    change_form_template = "admin/provider_request/change_form.html"

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'services':
            kwargs['widget'] = LabelWidget(model=Service)
        elif db_field.name == "verification_bases":
            kwargs['widget'] = LabelWidget(model=VerificationBasis)
        return super(ProviderRequest, self).formfield_for_dbfield(db_field,**kwargs)

    def send_approval_email(
        self,
        provider_request: ProviderRequest,
        request: HttpRequest,
        existing_provider: typing.Union[Hostingprovider, None],
    ):
        """
        Send an email to the provider whose request was approved by staff, changing
        the copy based on the state of the provider.
        """

        provider_url = provider_request.hostingprovider_set.first().admin_url
        context = {
            "username": provider_request.created_by.username,
            "org_name": provider_request.name,
            "update_url": request.build_absolute_uri(provider_url),
        }

        # For a new provider request, use this subject line
        subject = (
            f"Verification request to the Green Web Dataset is approved: "
            f"{mark_safe(provider_request.name)}"
        )

        if existing_provider:
            context["provider"] = provider_request.provider
            # For an update to an existing provider, use this subject line
            subject = (
                f"Update to the Green Web Dataset has been approved: "
                f"{mark_safe(provider_request.name)}"
            )

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
            subject=subject,
            context=context,
            template_txt="emails/verification_request_approved.txt",
            template_html="emails/verification_request_approved.html",
        )

    def log_message(
        self,
        provider_request: ProviderRequest,
        request: HttpRequest,
        message_type: int,
        message: str,
    ):
        """
        Log the approval, rejection or otherwise of a provider request
        """
        LogEntry.objects.log_action(
            user_id=request.user.id,
            content_type_id=ContentType.objects.get_for_model(provider_request).pk,
            object_id=provider_request.pk,
            object_repr=str(provider_request),
            action_flag=message_type,
            change_message=message,
        )

    @admin.action(description="Approve", permissions=["change"])
    def mark_approved(self, request, queryset):
        for provider_request in queryset:
            try:
                # check if this a request for an existing provider or not,
                # so we can send the appropriate email
                existing_provider = provider_request.provider
                hp = provider_request.approve()
                self.log_message(provider_request, request, CHANGE, "Approved")

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
                self.send_approval_email(provider_request, request, existing_provider)

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
            self.log_message(provider_request, request, CHANGE, "Rejected")

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
            self.log_message(provider_request, request, CHANGE, "Removed")

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

    @admin.action(description="Request changes", permissions=["change"])
    def mark_open(self, request, queryset):
        for provider_request in queryset:
            provider_request.status = ProviderRequestStatus.OPEN.value
            provider_request.save()
            self.log_message(provider_request, request, CHANGE, "Changes Requested")

            message = mark_safe(
                f"""
                    Request id <em>{provider_request.id}</em> for provider: \
                    <em>{provider_request.name}</em> has changed the status to OPEN,
                    making it available for editing and re-submitting.

                    They creator of this request has <em>not</em> been contacted yet -
                    you will need to contact them if appropriate.
                    """
            )
            self.message_user(request, message=message, level=messages.SUCCESS)
