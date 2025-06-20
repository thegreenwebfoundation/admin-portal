from django.contrib import messages
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe

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

from ..models import User

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


