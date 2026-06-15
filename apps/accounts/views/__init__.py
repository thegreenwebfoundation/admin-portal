import waffle

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic.base import TemplateView

from .api_keys import APIKeyCreateView, APIKeyIntrospectionView, APIKeyListView, APIKeyRevokeView
from .user import UserRegistrationView
from .user import UserActivationView
from .provider.autocomplete import (
    LabelAutocompleteView,
    LinkedProviderAutocompleteView,
    ProviderAutocompleteView,
)
from .provider.portal_home import ProviderPortalHomeView
from .provider.request.detail import ProviderRequestDetailView
from .provider.request.wizard import ProviderRequestWizardView
from .provider.carbon_txt import ProviderCarbonTxtView, ProviderCarbonTxtBuilderView


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    This dashboard view was what people would see when signing into the admin.
    We currently redirect to the provider portal home page as at present,we
    only really logged in activity by users who work for the providers in our system.
    """

    template_name = "dashboard.html"

    def get(self, request, *args, **kwargs):
        if waffle.flag_is_active(request, "api_keys"):
            return super().get(request, *args, **kwargs)
        else:
            return HttpResponseRedirect(reverse("provider_portal_home"))

