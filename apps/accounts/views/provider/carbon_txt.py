from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.utils.functional import cached_property

from guardian.shortcuts import get_users_with_perms

from ...models import Hostingprovider

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

