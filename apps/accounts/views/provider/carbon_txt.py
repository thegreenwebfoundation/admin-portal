from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.utils.functional import cached_property
from django.views.generic.base import TemplateView

from guardian.shortcuts import get_users_with_perms

from ...forms import CarbonTxtStep1Form, CarbonTxtStep2Form, CarbonTxtStep3Form
from ...models import Hostingprovider, ProviderCarbonTxt

from ...permissions import manage_provider


class ProviderRelatedResourceMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """
    This class handles permissions and object loading for resources related to a
    specific hosting provider (such as ProviderCarbonTxts).

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

class ProviderCarbonTxtView(ProviderRelatedResourceMixin, TemplateView):

    def get_context_data(self, form_data=None, *args, **kwargs):
        return { **super().get_context_data(*args, **kwargs), **{
            "form": self.get_form(form_data)
        }}

    def get_current_step(self):
        if not self.provider.has_carbon_txt:
            return 0
        else:
            carbon_txt = self.provider.carbon_txt
            returned_to_delegation_setup = self.request.GET.get("setup_delegation") == "1"
            pending_validation = carbon_txt.state == ProviderCarbonTxt.State.PENDING_VALIDATION
            pending_delegation = carbon_txt.state == ProviderCarbonTxt.State.PENDING_DELEGATION
            if pending_validation:
                return 1
            elif pending_delegation  or returned_to_delegation_setup:
                return 2
            else:
                return 3


    def get_template_names(self):
        return [
            "provider_portal/carbon_txt/step_1_domain.html",
            "provider_portal/carbon_txt/step_2_validation.html",
            "provider_portal/carbon_txt/step_3_delegation.html",
            "provider_portal/carbon_txt/step_4_complete.html",
        ][self.get_current_step()]


    def get_initial_data(self):
        return [
            { "domain": self.provider.website_domain },
            {},
            {},
            {}
        ][self.get_current_step()]

    def get_form_class(self):
        return [
            CarbonTxtStep1Form,
            CarbonTxtStep2Form,
            CarbonTxtStep3Form,
            None
        ][self.get_current_step()]

    def get_form(self, data=None):
        form_class = self.get_form_class()
        if form_class and data:
            return form_class(data)
        elif form_class:
            initial = self.get_initial_data()
            return form_class(initial=initial)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(request.POST, *args, **kwargs)
        form = context["form"]
        form.update_provider(self.provider)
        if form.is_valid():
            return HttpResponseRedirect(self.request.path)
        else:
            return self.render_to_response(context)
