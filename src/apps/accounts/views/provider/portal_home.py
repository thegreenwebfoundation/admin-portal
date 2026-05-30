from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from ...models import ProviderRequest, ProviderRequestStatus

class ProviderPortalHomeView(LoginRequiredMixin, ListView):
    """
    Home page of the Provider Portal:
    - used by external (non-staff) users to access a list of requests they submitted,
    - renders the list of pending verification requests as well as hosting providers on a HTML template,
    - requires the flag `provider_request` enabled for the user (otherwise returns 404).
    """

    template_name = "provider_portal/home.html"
    model = ProviderRequest

    def get_queryset(self) -> "dict[str, QuerySet[ProviderRequest]]":
        """
        Returns a dictionary with 2 querysets:
        - unapproved ProviderRequests created by the user,
        - all HostingProviders that the user has *explicit* object-level permissions to.
            This means: we don't show all possible providers for users who belong to the admin group or have staff status,
            only those where object-level permission between the user and the provider was explicitly granted.
        """
        return {
            "requests": ProviderRequest.objects.filter(created_by=self.request.user)
            .exclude(
                status__in=[
                    ProviderRequestStatus.APPROVED,
                    ProviderRequestStatus.REMOVED,
                ]
            )
            .order_by("name"),
            "providers": self.request.user.hosting_providers_explicit_perms.order_by(
                "name"
            ),
        }


