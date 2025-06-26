from collections import OrderedDict

from django.core.exceptions import ValidationError
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.views.generic import DetailView, ListView, CreateView, DeleteView

from formtools.wizard.views import SessionWizardView
from guardian.shortcuts import get_users_with_perms

from ...forms import (
    PreviewForm,
    LinkedDomainFormStep0,
)

from ...models import LinkedDomain, Hostingprovider

from ...permissions import manage_provider

from ...utils import validate_carbon_txt_for_domain

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
            mark_safe(
                f"""
                Thank you for taking the time to link the domain {domain}!<br />
                Your submission was recieved succesfully.<br />
                We review new linked domains on Tuesday each week.
                Once we have reviewed the request, we will contact you
                by email to let you know that it is approved, or that
                we need more information from you.
                """
            )
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

