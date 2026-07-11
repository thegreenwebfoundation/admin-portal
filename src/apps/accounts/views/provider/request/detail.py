from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView

from ....models import ProviderRequest

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


