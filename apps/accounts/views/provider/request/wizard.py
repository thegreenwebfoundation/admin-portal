from enum import Enum
import logging

from django.core.files.storage import DefaultStorage
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpRequest, Http404, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.safestring import mark_safe

from formtools.wizard.views import SessionWizardView

from ....forms import (
    BasisForVerificationForm,
    ConsentForm,
    GreenEvidenceForm,
    LocationStepForm,
    NetworkFootprintForm,
    OrgDetailsForm,
    PreviewForm,
    ServicesForm,
)

from ....models import (
    Hostingprovider,
    HostingproviderCertificate,
    ProviderRequest,
    ProviderRequestASN,
    ProviderRequestEvidence,
    ProviderRequestIPRange,
    ProviderRequestStatus,
)

from ....permissions import manage_provider

from ....utils import send_email

logger = logging.getLogger(__name__)

class ProviderRequestWizardView(LoginRequiredMixin, SessionWizardView):
    """
    Multi-step registration for providers.
    - uses `django-formtools` SessionWizardView to display
      the multi-step form over multiple screens,
    - requires the flag `provider_request` enabled to access the view,

    """

    file_storage = DefaultStorage()

    class Steps(Enum):
        """
        Pre-defined list of WizardView steps.
        WizardView uses numbers from 0 up, encoded as strings,
        to refer to specific steps.

        This Enum structure provides human-readable names
        for these steps.
        """

        ORG_DETAILS = "0"
        LOCATIONS = "1"
        SERVICES = "2"
        BASIS_FOR_VERIFICATION = "3"
        GREEN_EVIDENCE = "4"
        NETWORK_FOOTPRINT = "5"
        CONSENT = "6"
        PREVIEW = "7"

    FORMS = [
        (Steps.ORG_DETAILS.value, OrgDetailsForm),
        (Steps.LOCATIONS.value, LocationStepForm),
        (Steps.SERVICES.value, ServicesForm),
        (Steps.BASIS_FOR_VERIFICATION.value, BasisForVerificationForm),
        (Steps.GREEN_EVIDENCE.value, GreenEvidenceForm),
        (Steps.NETWORK_FOOTPRINT.value, NetworkFootprintForm),
        (Steps.CONSENT.value, ConsentForm),
        (Steps.PREVIEW.value, PreviewForm),
    ]

    TEMPLATES = {
        Steps.ORG_DETAILS.value: "provider_registration/about_org.html",
        Steps.LOCATIONS.value: "provider_registration/locations.html",
        Steps.SERVICES.value: "provider_registration/services.html",
        Steps.BASIS_FOR_VERIFICATION.value: "provider_registration/basis_for_verification.html",
        Steps.GREEN_EVIDENCE.value: "provider_registration/evidence.html",
        Steps.NETWORK_FOOTPRINT.value: "provider_registration/network_footprint.html",
        Steps.CONSENT.value: "provider_registration/consent.html",
        Steps.PREVIEW.value: "provider_registration/preview.html",
    }

    def log_creation(
        self,
        provider_request: ProviderRequest,
        request: HttpRequest,
        message_type: int = ADDITION,
        message: str = "Provider request created for review",
    ):
        """
        Log the creation of a new ProviderRequest instance
        """

        LogEntry.objects.log_action(
            user_id=request.user.id,
            content_type_id=ContentType.objects.get_for_model(provider_request).pk,
            object_id=provider_request.pk,
            object_repr=str(provider_request),
            action_flag=ADDITION,
            change_message=message,
        )

    def dispatch(self, request, *args, **kwargs):
        """
        This view is re-used for 3 different use cases:
        - /requests/new to submit a new verification request
        - /requests/{request_id}/edit to edit an existing request
        - /providers/{provider_id}/edit to edit an existing provider

        This method catches all the cases in which users should be stopped
        (e.g. lack of permissions or nonexistent objects) by raising exceptions
        and using HTTP redirects.
        It will proceed (by calling the same method on the parent class)
        if no issue was found.
        """
        request_id = kwargs.get("request_id")
        provider_id = kwargs.get("provider_id")

        if provider_id:
            # edit view can be only accessed for existing Providers
            try:
                hp = Hostingprovider.objects.get(id=provider_id)
            except Hostingprovider.DoesNotExist:
                raise Http404("Page not found")

            # only users with object-level perms for provider can access its edit view
            if (
                not request.user.has_perm(manage_provider.full_name, hp)
                and not request.user.is_admin
            ):
                messages.error(
                    self.request,
                    "You don't have the required permission to edit this listing",
                )
                return HttpResponseRedirect(reverse("provider_portal_home"))
        elif request_id:
            # edit view can be only accessed for existing PRs
            try:
                pr = ProviderRequest.objects.get(id=request_id)
            except ProviderRequest.DoesNotExist:
                raise Http404("Page not found")

            # only OPEN requests are editable
            if pr.status != ProviderRequestStatus.OPEN:
                messages.error(
                    self.request,
                    "This verification request cannot be edited at this time",
                )
                return HttpResponseRedirect(
                    reverse("provider_request_detail", args=[pr.pk])
                )
            # only admins and creators can access for editing existing requests
            if not request.user.is_admin and request.user.id != pr.created_by.id:
                raise Http404("Page not found")

        return super().dispatch(request, *args, **kwargs)

    def done(self, form_list, form_dict, **kwargs):
        """
        This method is called when all the forms are validated and submitted.

        Here we create objects for ProviderRequest and related models,
        based on the validated data from all Forms
        (passed as `form_dict`, where keys are the names of the steps).

        Because this method is called via POST request,
        it must return a redirect to a DetailView
        of a created ProviderRequest instance.

        Reference: https://django-formtools.readthedocs.io/en/latest/wizard.html#formtools.wizard.views.WizardView.done
        """  # noqa

        def _process_formset(formset, request):
            """
            Helper function to process the data from ModelFormSets used in this view
            """
            logger.info(f"formset: {formset.__class__.__name__}")
            logger.debug(f"formset: {formset.__class__.__name__}")
            if formset.__class__.__name__ == "ProviderRequestIPRangeFormFormSet":
                for form in formset.forms:
                    logger.debug(form.__class__.__name__)
                    logger.debug(f"form.has_changed(): {form.has_changed()}")

            instances = formset.save(commit=False)
            for instance in instances:
                instance.request = request
                instance.save()

            for object_to_delete in formset.deleted_objects:
                logger.debug(
                    f"we have {len(formset.deleted_objects)} objects to delete"
                )
                object_to_delete.delete()

            logger.debug(
                f"checking for changed forms: {formset.form.__class__.__name__}"
            )
            if formset.changed_objects:
                logger.debug(
                    f"we have {len(formset.changed_objects)} objects to change"
                )

        steps = ProviderRequestWizardView.Steps

        # process ORG_DETAILS form: extract ProviderRequest and Location
        org_details_form = form_dict[steps.ORG_DETAILS.value]
        pr = org_details_form.save(commit=False)
        pr.save()

        # process LOCATIONS form: extract locations
        locations_formset = form_dict[steps.LOCATIONS.value].forms["locations"]
        _process_formset(locations_formset, pr)

        # process LOCATION: check if a bulk location import is needed
        extra_location_form = form_dict[steps.LOCATIONS.value].forms["extra"]
        location_import_required = extra_location_form.cleaned_data[
            "location_import_required"
        ]

        pr.location_import_required = bool(location_import_required)

        # process SERVICES form: assign services to ProviderRequest
        services_form = form_dict[steps.SERVICES.value]
        service_slugs = services_form.cleaned_data["services"]
        pr.set_services_from_slugs(service_slugs)
        pr.created_by = self.request.user
        pr.save()

        # process BASIS_FOR_VERIFICATION form: assign verification bases to ProviderRequest
        verification_bases_form = form_dict[steps.BASIS_FOR_VERIFICATION.value]
        verification_bases_slugs = verification_bases_form.cleaned_data["verification_bases"]
        pr.set_verification_bases_from_slugs(verification_bases_slugs)

        # process GREEN_EVIDENCE form: link evidence to ProviderRequest
        evidence_formset = form_dict[steps.GREEN_EVIDENCE.value]
        _process_formset(evidence_formset, pr)

        # process NETWORK_FOOTPRINT form: retrieve IP ranges
        ip_range_formset = form_dict[steps.NETWORK_FOOTPRINT.value].forms["ips"]
        _process_formset(ip_range_formset, pr)

        # process NETWORK_FOOTPRINT form: retrieve ASNs
        asn_formset = form_dict[steps.NETWORK_FOOTPRINT.value].forms["asns"]
        _process_formset(asn_formset, pr)

        # process NETWORK_FOOTPRINT form: retrieve network explanation
        # if network data is missing
        extra_network_form = form_dict[steps.NETWORK_FOOTPRINT.value]["extra"]
        network_explanation = extra_network_form.cleaned_data.get(
            "missing_network_explanation"
        )
        network_import_required = extra_network_form.cleaned_data.get(
            "network_import_required"
        )
        pr.missing_network_explanation = network_explanation
        pr.network_import_required = bool(network_import_required)
        pr.save()

        # process CONSENT form
        consent_form = form_dict[steps.CONSENT.value]
        data_processing_opt_in = consent_form.cleaned_data.get("data_processing_opt_in")
        newsletter_opt_in = consent_form.cleaned_data.get("newsletter_opt_in")
        pr.data_processing_opt_in = bool(data_processing_opt_in)
        pr.newsletter_opt_in = bool(newsletter_opt_in)
        pr.save()

        # if this view was used to edit an existing hosting provider,
        # mark its ID in the new ProviderRequest object
        provider_id = self.kwargs.get("provider_id")
        if provider_id:
            try:
                pr.provider = Hostingprovider.objects.get(id=provider_id)
            except Hostingprovider.DoesNotExist:
                # fallback to creating a new provider
                pr.provider = None

        # set status
        pr.status = ProviderRequestStatus.PENDING_REVIEW.value
        pr.save()

        # log the creation in the history of this request so we have an accessble audit trail
        self.log_creation(pr, self.request)

        # send an email notification to the author and green web staff
        self._send_notification_email(pr)

        # display a notification on the next page
        messages.success(
            self.request,
            """
            Thank you!

            Your verification request was submitted successfully.
            We have sent you an email with confirmation and a link that summarises your submitted info.
            We are now reviewing your request - we'll be in touch soon.
            """,
        )
        return redirect(pr)

    def get_template_names(self):
        """
        Configures a template for each step of the Wizard.

        Reference: https://docs.djangoproject.com/en/3.2/ref/class-based-views/mixins-simple/#django.views.generic.base.TemplateResponseMixin.get_template_names
        """  # noqa
        return [self.TEMPLATES[self.steps.current]]

    def _get_data_for_preview(self):
        """
        Gathers cleaned data from all the steps preceding the PREVIEW step,
        so that it can be rendered on a single page.

        Returns a dictionary with key-value pairs:
        - key: name of the step,
        - value: an unbound form from that step, with initial data populated.

        _______
        Gotchas:

        - The forms are not bound: `form.data` will return {}.
        The initial data should be accessed through iterating over bound fields:
        `field.value for field in form`.
        - Iterating over the fields like mentioned above will also include
        the "id" field for ModelForms and ModelFormSets, as well as "DELETE" field
        to mark deleted forms in the formsets. To render forms without these fields in the templates
        it's recommended to use the the template tag "exclude_preview_fields".
        - Forms marked for deletion are also passed to the preview step, that's why
        it's necessary to filter them out in the template (based on the value of the DELETE field).
        """

        preview_forms = {}
        # iterate over all forms without the last one (PREVIEW)
        for step, form in self.FORMS[:-1]:
            cleaned_data = self.get_cleaned_data_for_step(step)
            preview_forms[step] = form(initial=cleaned_data)
        return preview_forms

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)
        if self.steps.current == self.Steps.PREVIEW.value:
            # inject data from all previous steps for rendering
            context["preview_forms"] = self._get_data_for_preview()
        return context

    def get_form_kwargs(self, step=None):
        """
        Workaround for injecting "instance" argument to MultiModelForm
        when the form is used for editing existing request
        """
        affected_steps = [
            self.Steps.LOCATIONS.value,
            self.Steps.NETWORK_FOOTPRINT.value,
        ]
        if self.kwargs.get("request_id") and step in affected_steps:
            return {"instance": self.get_form_instance(step)}
        return {}

    def _send_notification_email(self, provider_request: ProviderRequest):
        """
        Send notification to support staff, and the user to acknowledge their submission.
        """  # noqa

        current_site = get_current_site(self.request)
        connection_scheme = self.request.scheme
        user = self.request.user
        request_path = reverse("provider_request_detail", args=[provider_request.id])

        link_to_verification_request = (
            f"{connection_scheme}://{current_site.domain}{request_path}"
        )

        ctx = {
            "org_name": provider_request.name,
            "status": provider_request.status,
            "link_to_verification_request": link_to_verification_request,
        }

        # For a new provider request, use this subject line
        subject = (
            f"Your Green Web Dataset verification request: "
            f"{mark_safe(provider_request.name)}"
        )

        if provider_request.provider:
            ctx["provider"] = provider_request.provider
            # For an update to an existing provider, use this subject line
            subject = (
                f"Your Green Web Dataset update request: "
                f"{mark_safe(provider_request.name)}"
            )

        send_email(
            address=user.email,
            subject=subject,
            context=ctx,
            template_html="emails/verification-request-notify.html",
            template_txt="emails/verification-request-notify.txt",
            bcc=settings.TRELLO_REGISTRATION_EMAIL_TO_BOARD_ADDRESS,
        )

    @classmethod
    def get_instance_dict(cls, request_id):
        """
        Based on request_id, return existing instances of ProviderRequest
        and related objects in a map that matches the structure of the forms.
        """
        try:
            pr_instance = ProviderRequest.objects.get(id=request_id)
        except ProviderRequest.DoesNotExist:
            return {}

        location_qs = (
            pr_instance.providerrequestlocation_set.all()
            if pr_instance.providerrequestlocation_set.exists()
            else ProviderRequestASN.objects.none()
        )
        evidence_qs = (
            pr_instance.providerrequestevidence_set.all()
            if pr_instance.providerrequestevidence_set.exists()
            else ProviderRequestEvidence.objects.none()
        )
        asn_qs = (
            pr_instance.providerrequestasn_set.all()
            if pr_instance.providerrequestasn_set.exists()
            else ProviderRequestASN.objects.none()
        )
        ip_qs = (
            pr_instance.providerrequestiprange_set.all()
            if pr_instance.providerrequestiprange_set.exists()
            else ProviderRequestIPRange.objects.none()
        )

        instance_dict = {
            cls.Steps.ORG_DETAILS.value: pr_instance,
            cls.Steps.LOCATIONS.value: {
                "locations": location_qs,
                "extra": pr_instance,
            },
            cls.Steps.SERVICES.value: pr_instance,
            cls.Steps.BASIS_FOR_VERIFICATION.value: pr_instance,
            cls.Steps.GREEN_EVIDENCE.value: evidence_qs,
            cls.Steps.NETWORK_FOOTPRINT.value: {
                "ips": ip_qs,
                "asns": asn_qs,
                "extra": pr_instance,
            },
            cls.Steps.CONSENT.value: pr_instance,
        }
        return instance_dict

    @classmethod
    def get_initial_dict(cls, provider_id):
        """
        Based on provider_id, return data about existing Hostingprovider
        in a format expected by the consecutive forms of WizardView
        """

        def _evidence_initial_data(evidence: HostingproviderCertificate):
            return {
                "title": evidence.title,
                "description": evidence.description,
                "link": evidence.url,
                "file": evidence.attachment,
                "type": evidence.type,
                "public": evidence.public,
            }

        def _location_initial_data(hosting_provider: Hostingprovider):
            """
            Accept a hosting provider instance and return a list of
            locations in a format expected by the form.
            Fetches locations from the request if it exists, otherwise
            the single location originally associated with the provider.
            """

            hp_provider_request = hosting_provider.request

            if hp_provider_request:
                locations = hp_provider_request.providerrequestlocation_set.all()
                # return only the locations that are associated with the request
                return [
                    {
                        "city": location.city,
                        "country": location.country,
                        "name": location.name,
                    }
                    for location in locations
                ]

            return [
                {
                    "city": hosting_provider.city,
                    "country": hosting_provider.country,
                }
            ]

        def _org_details_initial_data(hosting_provider: Hostingprovider):
            initial_org_dict = {
                "name": hosting_provider.name,
                "website": hosting_provider.website,
                "description": hosting_provider.description,
            }
            hp_provider_request = hosting_provider.request
            if hp_provider_request:
                initial_org_dict["authorised_by_org"] = (
                    hp_provider_request.authorised_by_org
                )
            return initial_org_dict

        def _network_footprint_initial_data(hosting_provider: Hostingprovider):
            hp_provider_request = hosting_provider.request
            network_dict = {
                # TODO: all IP ranges / ASNs or only active ones?
                "ips": [
                    {"start": range.ip_start, "end": range.ip_end}
                    for range in hosting_provider.greencheckip_set.all()
                ],
                "asns": [
                    {"asn": item.asn}
                    for item in hosting_provider.greencheckasn_set.all()
                ],
            }
            if hp_provider_request:
                network_dict["extra"] = {
                    "network_import_required": hp_provider_request.network_import_required,
                    "missing_network_explanation": hp_provider_request.missing_network_explanation,
                }
            return network_dict

        try:
            hp_instance = Hostingprovider.objects.get(id=provider_id)
        except Hostingprovider.DoesNotExist:
            return {}

        initial_dict = {
            cls.Steps.ORG_DETAILS.value: _org_details_initial_data(hp_instance),
            cls.Steps.LOCATIONS.value: {
                # TODO: update this when HP has multiple locations, not just the
                # provider request
                "locations": _location_initial_data(hp_instance),
            },
            cls.Steps.SERVICES.value: {
                "services": [s for s in hp_instance.services.slugs()]
            },
            cls.Steps.BASIS_FOR_VERIFICATION.value: {
                "verification_bases": [b for b in hp_instance.verification_bases.slugs()]
            },
            cls.Steps.GREEN_EVIDENCE.value: [
                _evidence_initial_data(ev)
                for ev in hp_instance.supporting_documents.all()
            ],
            cls.Steps.NETWORK_FOOTPRINT.value: _network_footprint_initial_data(
                hp_instance
            ),
            cls.Steps.CONSENT.value: {},
        }

        return initial_dict
