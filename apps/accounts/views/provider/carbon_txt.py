from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.utils.functional import cached_property
from django.views.generic.base import TemplateView

from guardian.shortcuts import get_users_with_perms

from ...forms import CarbonTxtStep1Form, CarbonTxtStep3Form
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

    def get_template_names(self):
        if not self.provider.has_carbon_txt:
            return "provider_portal/carbon_txt/step_1_domain.html"
        elif self.provider.carbon_txt.state == ProviderCarbonTxt.State.PENDING_VALIDATION:
            return "provider_portal/carbon_txt/step_2_validation.html"
        elif self.provider.carbon_txt.state == ProviderCarbonTxt.State.PENDING_DELEGATION:
            return "provider_portal/carbon_txt/step_3_delegation.html"
        else:
            return "provider_portal/carbon_txt/step_4_complete.html"

    def get_form(self, data=None):
        if not self.provider.has_carbon_txt:
            if data:
                return CarbonTxtStep1Form(data)
            else:
                return CarbonTxtStep1Form(initial={
                    "domain": self.provider.website_domain
                })
        elif self.provider.carbon_txt.state == ProviderCarbonTxt.State.PENDING_VALIDATION:
            return None
        elif self.provider.carbon_txt.state == ProviderCarbonTxt.State.PENDING_DELEGATION:
            if data:
                return CarbonTxtStep3Form(data)
            else:
                return CarbonTxtStep3Form()
        else:
            return None

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(request.POST, *args, **kwargs)
        form = context["form"]
        if form.is_valid():
            form.update_provider(self.provider)
            return HttpResponseRedirect("")
        else:
            return self.render_to_response(context)
