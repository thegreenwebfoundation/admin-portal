

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.encoding import force_text

from django_registration.backends.activation.views import RegistrationView
from django_registration.backends.activation.views import ActivationView
from django_registration.forms import RegistrationFormCaseInsensitive
from django_registration import signals
from django_registration.exceptions import ActivationError


class AdminRegistrationView(RegistrationView):
    form = RegistrationFormCaseInsensitive
    template_name = 'registration.html'

    email_body_template = 'emails/activation.html'
    email_subject_template = 'emails/activation_subject.txt'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['site_header'] = 'Register a new user'
        return context

    def get_success_url(self, user=None):
        """
        Return the URL to redirect to after successful redirection.
        """
        return '/admin/'

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            messages.add_message(
                request, messages.INFO,
                'Check your email to activate the user'
            )
        return super().post(request, *args, **kwargs)


class AdminActivationView(ActivationView):

    def get_success_url(self, user=None):
        return '/admin/'

    def get(self, *args, **kwargs):
        """
        We override the get method here because we only want to use the admin
        page and show the user a message.
        """
        activation = {'activation_key': self.request.GET.get('activation_key')}
        try:
            activated_user = self.activate(*args, **activation)
        except ActivationError as e:
            error_message = e.message
        else:
            signals.user_activated.send(
                sender=self.__class__,
                user=activated_user,
                request=self.request
            )
            message = 'Your user is activated, you can now login'
            messages.add_message(self.request, messages.SUCCESS, message)
            return HttpResponseRedirect(force_text(
                self.get_success_url(activated_user)
            ))

        messages.add_message(self.request, messages.ERROR, error_message)
        return HttpResponseRedirect(force_text(
            self.get_success_url()
        ))
