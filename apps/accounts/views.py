import waffle
import os
from waffle.mixins import WaffleFlagMixin
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from django.contrib.auth.models import Group
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.query import QuerySet
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.encoding import force_text
from django.views.generic import UpdateView, DetailView, ListView
from django.views.generic.base import TemplateView
from django.shortcuts import render
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
    template_name = "provider_registration/formset.html"
    waffle_flag = "provider_request"
    form_list = [RegistrationForm1, RegistrationForm2, RegistrationForm3, RegistrationForm4]
    file_storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'registration_evidence'))
    def done(self, form_list, **kwargs):
        return HttpResponseRedirect("/done/")

    def get_form_initial(self, step):
        initial = self.initial_dict.get(step, {})
        # populate the location on step1 using data from step0
        if step == "1":
            prev_step_data = self.get_cleaned_data_for_step("0")
            location_keys = ["country", "city", "services"]
            location_data = dict(
                [(k, v) for k, v in prev_step_data.items() if k in location_keys]
            )
            # step1 is a formset, so initial data needs to be a sequence
            return [location_data]

        return initial
