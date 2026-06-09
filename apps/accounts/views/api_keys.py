from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.generic import FormView, TemplateView
from rest_framework.response import Response
from rest_framework.views import APIView

from ..forms import APIKeyForm, APIRevokeForm
from ..models import APIKey
from ..permissions import HasGWFSharedSecret

class APIKeyIntrospectionView(APIView):
    """
    Internal: called by other services to validate a key.
    Protected by a shared secret — not user-facing.
    """
    permission_classes = [HasGWFSharedSecret]

    def post(self, request):
        raw_key = request.data.get("token", "")

        try:
            key = APIKey.objects.get_from_key(raw_key)
            return Response({
                "active": True,
                "user_id": key.user_id,
                "username": key.user.username,
                "expiry_date": key.expiry_date,
                "prefix": key.prefix,
                "service": key.service.key,
                "privilege_level": key.privilege_level.name if key.privilege_level else None
            })
        except APIKey.DoesNotExist:
            return Response({"active": False})

class APIKeyListView(LoginRequiredMixin, TemplateView):
    template_name = "api_keys/list.html"


class APIKeyCreateView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """
    Displays the new API key form, then renders an interstitial page which
    reveals the token so that it can be copied by the user.
    """

    template_name = "api_keys/create.html"
    form_class = APIKeyForm

    def get_success_url(self):
        messages.success(self.request, f"API key {self.key.displayable_prefix} created!")
        return reverse("list-api-keys")

    def has_permission(self):
        return self.request.user.can_create_api_key

    def form_valid(self, form):
        (key, token) = form.create_key(self.request.user)
        context = self.get_context_data(form=form, key=key, token=token)
        return TemplateResponse(self.request, "api_keys/created.html", context)

class APIKeyRevokeView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """
    Revokes an API key, showing an interstitial dummy form for confirmation
    """
    template_name = "api_keys/revoke.html"
    form_class = APIRevokeForm
    raise_exception = True # If the user does not have permission we 403, rather than redirecting to login.

    @cached_property
    def key(self):
        return get_object_or_404(APIKey, prefix=self.kwargs["key_prefix"])

    def has_permission(self):
        return self.request.user == self.key.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["key"] = self.key
        return context

    def get_success_url(self):
        messages.success(self.request, f"API key {self.key.displayable_prefix} revoked!")
        return reverse("list-api-keys")

    def form_valid(self, form):
        self.key.revoked = True
        self.key.save()
        return super().form_valid(form)
