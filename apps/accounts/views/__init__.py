from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic.base import TemplateView

from .user import UserRegistrationView
from .user import UserActivationView
from .provider.domains import (
        ProviderDomainsView,
        ProviderDomainCreateView,
        ProviderDomainDeleteView,
        ProviderDomainDetailView
)
from .provider.autocomplete import LabelAutocompleteView, ProviderAutocompleteView
from .provider.portal_home import ProviderPortalHomeView
from .provider.request.detail import ProviderRequestDetailView
from .provider.request.wizard import ProviderRequestWizardView


class DashboardView(TemplateView):
    """
    This dashboard view was what people would see when signing into the admin.
    We currently redirect to the provider portal home page as at present,we
    only really logged in activity by users who work for the providers in our system.
    """

    template_name = "dashboard.html"

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse("provider_portal_home"))

