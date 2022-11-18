import waffle
from waffle.mixins import WaffleFlagMixin
from enum import Enum
from django.conf import settings
from django.core.files.storage import DefaultStorage
from django.contrib import messages
from django.contrib.auth.models import Group
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.query import QuerySet
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils.encoding import force_text
from django.views.generic import UpdateView, DetailView, ListView
from django.views.generic.base import TemplateView
from django_registration import signals
from django_registration.backends.activation.views import (
    ActivationView,
    RegistrationView,
)

from django_registration.exceptions import ActivationError
from django_registration.forms import RegistrationFormCaseInsensitive
from formtools.wizard.views import SessionWizardView

from .forms import (
    UserUpdateForm,
    RegistrationForm1,
    RegistrationForm2,
    RegistrationForm3,
    RegistrationForm4,
    IpRangeForm,
)
from .models import User, ProviderRequest


class RegistrationForm(RegistrationFormCaseInsensitive):
    class Meta(RegistrationFormCaseInsensitive.Meta):
        model = User


class DashboardView(TemplateView):

    template_name = "dashboard.html"

    def get(self, request, *args, **kwargs):
        if waffle.flag_is_active(request, "dashboard"):
            return super().get(request, args, kwargs)
        else:
            return HttpResponseRedirect(reverse("greenweb_admin:index"))


class AdminRegistrationView(RegistrationView):
    form_class = RegistrationForm
    template_name = "registration.html"

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
        return reverse("admin:index")

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            messages.add_message(
                request, messages.INFO, "Check your email to activate the user"
            )
        return super().post(request, *args, **kwargs)


class AdminActivationView(ActivationView):
    def get_success_url(self, user=None):
        return reverse("admin:index")

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
            message = "Your user is activated, you can now login"
            messages.add_message(self.request, messages.SUCCESS, message)
            return HttpResponseRedirect(
                force_text(self.get_success_url(activated_user))
            )

        messages.add_message(self.request, messages.ERROR, error_message)
        return HttpResponseRedirect(force_text(self.get_success_url()))


class UserUpdateView(UpdateView):
    """
    A view for allowing users to edit basic details, and control
    notification settings
    """

    model = User
    form_class = UserUpdateForm

    def get(self, request, *args, **kwargs):
        """Handle GET requests: instantiate a blank version of the form."""
        return super().get(request, args, kwargs)


class ProviderRequestListView(LoginRequiredMixin, WaffleFlagMixin, ListView):
    """
    List view for ProviderRequests:
    - used by external (non-staff) users to access a list of requests they submitted,
    - renders the list of requests on a HTML template,
    - requires the flag `provider_request` enabled for the user (otherwise returns 404).
    """

    template_name = "provider_request/list.html"
    waffle_flag = "provider_request"
    model = ProviderRequest

    def get_queryset(self) -> "QuerySet[ProviderRequest]":
        return ProviderRequest.objects.filter(created_by=self.request.user)


class ProviderRequestDetailView(LoginRequiredMixin, WaffleFlagMixin, DetailView):
    """
    Detail view for ProviderRequests:
    - used by external (non-staff) users to view a summary of a single request they submitted,
    - renders a single provider request on a HTML template,
    - requires the flag `provider_request` enabled for the user (otherwise returns 404).
    """

    template_name = "provider_request/detail.html"
    waffle_flag = "provider_request"
    model = ProviderRequest

    def get_queryset(self) -> "QuerySet[ProviderRequest]":
        return ProviderRequest.objects.filter(created_by=self.request.user)


class ProviderRegistrationView(SessionWizardView):
    """
    Uses django-formtools WizardView to display multi-step form
    over multiple screens
    """

    class Steps(Enum):
        """
        Pre-defined list of WizardView steps (screens).
        WizardView uses numbers from 0 up, encoded as strings,
        to refer to specific steps.

        This Enum structure aims to provide human-readable names
        for these steps.
        """

        ORG_DETAILS = "0"
        SERVICES = "1"
        GREEN_EVIDENCE = "2"
        NETWORK_FOOTPRINT = "3"

    FORMS = [
        (Steps.ORG_DETAILS.value, RegistrationForm1),
        (Steps.SERVICES.value, RegistrationForm2),
        (Steps.GREEN_EVIDENCE.value, RegistrationForm3),
        (Steps.NETWORK_FOOTPRINT.value, RegistrationForm4),
    ]

    TEMPLATES = {
        Steps.ORG_DETAILS.value: "provider_registration/form.html",
        Steps.SERVICES.value: "provider_registration/form.html",
        Steps.GREEN_EVIDENCE.value: "provider_registration/formset.html",
        Steps.NETWORK_FOOTPRINT.value: "provider_registration/multiform.html",
    }

    waffle_flag = "provider_request"
    file_storage = DefaultStorage()

    def done(self, form_list, **kwargs):
        # TODO: implement this! data should be persisted.
        # for now it returns a JSON summary of the output
        # with a hack to avoid serializing UploadedFile (uses its name instead)
        # a single item in form_list is a list in case of a formset!
        resp = {"form_data": [form.cleaned_data for form in form_list]}
        resp["form_data"][-1][0]["file"] = resp["form_data"][-1][0]["file"].name
        return JsonResponse(resp)

    def get_template_names(self):
        return [self.TEMPLATES[self.steps.current]]

    def get_form_initial(self, step):
        """
        Populate the location on step1 using data from step0
        """
        initial = self.initial_dict.get(step, {})
        STEPS = ProviderRegistrationView.Steps

        if step == STEPS.SERVICES.value:
            prev_step_data = self.get_cleaned_data_for_step(STEPS.ORG_DETAILS.value)
            location_keys = [
                "country",
                "city",
            ]
            location_data = dict(
                [(k, v) for k, v in prev_step_data.items() if k in location_keys]
            )
            return location_data

        return initial

    def get_context_data(self, form, **kwargs):
        """
        TODO: remove this if not needed (after debugging is done)
        """
        context = super().get_context_data(form=form, **kwargs)
        return context
