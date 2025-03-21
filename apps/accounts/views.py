import logging

from enum import Enum
from collections import OrderedDict

from dal import autocomplete
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.models import LogEntry, ADDITION

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.shortcuts import get_current_site
from django.core.files.storage import DefaultStorage
from django.core.exceptions import ValidationError
from django.db.models.query import QuerySet
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe
from django.utils.functional import cached_property
from django.views.generic import DetailView, ListView, CreateView, DeleteView
from django.views.generic.base import TemplateView
from django.views.generic.edit import ModelFormMixin

from django_registration import signals, validators
from django_registration.backends.activation.views import (
    ActivationView,
    RegistrationView,
)
from django_registration.exceptions import ActivationError
from django_registration.forms import (
    RegistrationFormCaseInsensitive,
    RegistrationFormUniqueEmail,
)
from formtools.wizard.views import SessionWizardView

from guardian.shortcuts import get_users_with_perms

from .forms import (
    BasisForVerificationForm,
    ConsentForm,
    GreenEvidenceForm,
    LocationStepForm,
    NetworkFootprintForm,
    OrgDetailsForm,
    PreviewForm,
    ServicesForm,
    LinkedDomainFormStep0,
)
from .models import (
    Hostingprovider,
    HostingproviderCertificate,
    ProviderRequest,
    ProviderRequestASN,
    ProviderRequestEvidence,
    ProviderRequestIPRange,
    ProviderRequestStatus,
    User,
    LinkedDomain,
)
from .permissions import manage_provider
from .utils import (send_email, validate_carbon_txt_for_domain)
from django.http import HttpRequest

logger = logging.getLogger(__name__)


class DashboardView(TemplateView):
    """
    This dashboard view was what people would see when signing into the admin.
    We currently redirect to the provider portal home page as at present,we
    only really logged in activity by users who work for the providers in our system.
    """

    template_name = "dashboard.html"

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse("provider_portal_home"))


class ProviderAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # if a user is not authenticated don't show anything
        if not self.request.user.is_admin:
            return Hostingprovider.objects.none()

        # we only want active hosting providers to allocate to
        qs = Hostingprovider.objects.exclude(archived=True)

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class RegistrationForm(RegistrationFormCaseInsensitive, RegistrationFormUniqueEmail):
    def __init__(self, *args, **kwargs):
        # override error message for unique email validation
        validators.DUPLICATE_EMAIL = mark_safe(
            """This email address is already in use.
            If this is your email address, you can <a href="/accounts/login/">log in</a>
            or do a <a href="/accounts/password_reset/">password reset</a>"""
        )
        super().__init__(*args, **kwargs)

    class Meta(RegistrationFormCaseInsensitive.Meta):
        model = User


class UserRegistrationView(RegistrationView):
    form_class = RegistrationForm
    email_body_template = "emails/activation.html"
    email_subject_template = "emails/activation_subject.txt"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["site_header"] = "Register a new user"
        return context

    def create_inactive_user(self, form):
        new_user = super().create_inactive_user(form)
        groups = Group.objects.filter(name__in=["hostingprovider", "datacenter"])

        for group in groups:
            new_user.groups.add(group)
        new_user.save()
        return new_user

    def get_success_url(self, user=None):
        """
        Return the URL to redirect to after successful redirection.
        """
        # stay on the same page
        return reverse("registration")

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            messages.success(
                request,
                "We've sent you an email. You need to follow the link in the email to confirm your address to finish signing up.",
            )
        return super().post(request, *args, **kwargs)


class UserActivationView(ActivationView):
    def get_success_url(self, user=None):
        return reverse("login")

    def get(self, *args, **kwargs):
        """
        We override the get method here because we only want to use the admin
        page and show the user a message.
        """
        try:
            activated_user = self.activate(*args, **kwargs)
        except ActivationError as e:
            error_message = e.message
        else:
            signals.user_activated.send(
                sender=self.__class__, user=activated_user, request=self.request
            )
            message = "Thanks, we've confirmed your email address. Now you can login with your username and password."
            messages.success(self.request, message)
            return HttpResponseRedirect(force_str(self.get_success_url(activated_user)))

        messages.error(self.request, error_message)
        return HttpResponseRedirect(force_str(self.get_success_url()))


class ProviderRelatedResourceMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """
    This class handles permissions and object loading for resources related to a
    specific hosting provider (such as LinkedDomains).

    Mixing it into a view ensures that:
        - the self.provider property is populated appropriately
        - the `provider` is passed in the template context
        . the view is only accessible to admins or the provider's owner
            (returning a 403 otherwise)
    """

    @cached_property
    def provider(self):
        provider_id = self.kwargs.get("provider_id")
        return Hostingprovider.objects.get(pk=provider_id)

    def has_permission(self):
        allowed_users= get_users_with_perms(
                self.provider,
                only_with_perms_in=(manage_provider.codename,),
                with_superusers=True,
                with_group_users=True,
        )
        return self.request.user in allowed_users

    def get_context_data(self, *args, **kwargs):
        return { **super().get_context_data(*args, **kwargs), **{
            "provider": self.provider
        }}

class ProviderDomainsView(ProviderRelatedResourceMixin, ListView):
    """
    Domain hash home page:
    - used by external (non-staff) users to see a list of domain hashes they have created,
    - renders the list of domain hashes a HTML template,
    - requires the flag `domain_hash` enabled for the user (otherwise returns 404).
    """

    template_name = "provider_portal/provider_domains_index.html"
    model = LinkedDomain


    def get_queryset(self):
        return self.provider.linkeddomain_set.all()


class ProviderDomainCreateView(ProviderRelatedResourceMixin, SessionWizardView):

    FORMS = [
         ("0", LinkedDomainFormStep0),
         ("1", PreviewForm),
    ]

    TEMPLATES = {
        "0": "provider_portal/provider_domain_new/step_0.html",
        "1": "provider_portal/provider_domain_new/step_1.html"
    }

    def _get_data_for_preview(self):
        preview_data = {}
        current_step = int(self.steps.current or 0)
        for step in range(0, current_step):
            cleaned_data = self.get_cleaned_data_for_step(str(step))
            preview_data[str(step)] = cleaned_data
        return preview_data


    def get_template_names(self):
        return [self.TEMPLATES[self.steps.current]]

    def get_context_data(self, *args, **kwargs):
        return { **super().get_context_data(*args, **kwargs), **{
            "preview_data": self._get_data_for_preview()
        }}

    def get_success_url(self):
        return reverse('provider-domain-index', kwargs={'provider_id': self.provider.id})


    def done(self, form_list, form_dict, **kwargs):
        domain = form_dict["0"].save(commit=False)
        domain.provider = self.provider
        domain.created_by = self.request.user
        validate_carbon_txt_for_domain(domain.domain)
        domain.save()
        messages.success(
            self.request,
            """
            Thank you!

            Your linked domain was submitted succesfully.
            We are now reviewing your request - we'll be in touch soon.
            """
        )
        return redirect(self.get_success_url())

    def render_done(self, form, **kwargs):
        # This method is copied from the Wizard base class, and overridden with a try/except block
        # in order to allow us to add extra validation in the `done` method,
        # see https://github.com/jazzband/django-formtools/issues/61#issuecomment-199702599.
        # This allows us to check for the presence of carbon.txt when the wizard completes,
        # and allow the user to retry if necessary.
        final_forms = OrderedDict()
        for form_key in self.get_form_list():
            form_obj = self.get_form(
                step=form_key,
                data=self.storage.get_step_data(form_key),
                files=self.storage.get_step_files(form_key)
            )
            if not form_obj.is_valid():
                return self.render_revalidation_failure(form_key, form_obj, **kwargs)
            final_forms[form_key] = form_obj

        try:
            done_response = self.done(list(final_forms.values()), form_dict=final_forms, **kwargs)
            self.storage.reset()
            return done_response
        except ValidationError as e:
            form.add_error(None, e)
            return self.render(form)

class ProviderDomainDetailView(ProviderRelatedResourceMixin, DetailView):
    template_name = "provider_portal/provider_domain_detail.html"

    def get_object(self):
        domain = self.kwargs.get("domain")
        return get_object_or_404(
            LinkedDomain.objects.filter(provider=self.provider.id,domain=domain)
        )

class ProviderDomainDeleteView(ProviderRelatedResourceMixin, DeleteView):
    template_name = "provider_portal/provider_domain_delete.html"
    model = LinkedDomain


    def get_object(self):
        domain = self.kwargs.get("domain")
        return get_object_or_404(
            LinkedDomain.objects.filter(provider=self.provider.id,domain=domain)
        )

    def get_success_url(self):
        return reverse("provider-domain-index", args=(self.kwargs.get("provider_id"),))

class ProviderPortalHomeView(LoginRequiredMixin, ListView):
    """
    Home page of the Provider Portal:
    - used by external (non-staff) users to access a list of requests they submitted,
    - renders the list of pending verification requests as well as hosting providers on a HTML template,
    - requires the flag `provider_request` enabled for the user (otherwise returns 404).
    """

    template_name = "provider_portal/home.html"
    model = ProviderRequest

    def get_queryset(self) -> "dict[str, QuerySet[ProviderRequest]]":
        """
        Returns a dictionary with 2 querysets:
        - unapproved ProviderRequests created by the user,
        - all HostingProviders that the user has *explicit* object-level permissions to.
            This means: we don't show all possible providers for users who belong to the admin group or have staff status,
            only those where object-level permission between the user and the provider was explicitly granted.
        """
        return {
            "requests": ProviderRequest.objects.filter(created_by=self.request.user)
            .exclude(
                status__in=[
                    ProviderRequestStatus.APPROVED,
                    ProviderRequestStatus.REMOVED,
                ]
            )
            .order_by("name"),
            "providers": self.request.user.hosting_providers_explicit_perms.order_by(
                "name"
            ),
        }


class ProviderRequestDetailView(LoginRequiredMixin, DetailView):
    """
    Detail view for ProviderRequests:
    - used by external (non-staff) users to view a summary of a single request they submitted,
    - renders a single provider request on a HTML template,
    - requires the flag `provider_request` enabled for the user (otherwise returns 404).
    """  # noqa

    template_name = "provider_portal/request_detail.html"
    model = ProviderRequest

    def get_queryset(self) -> "QuerySet[ProviderRequest]":
        """
        Admins can retrieve any ProviderRequest object,
        regular users can only retrieve objects that they created.
        """
        if self.request.user.is_admin:
            return ProviderRequest.objects.all()
        return ProviderRequest.objects.filter(created_by=self.request.user)


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
