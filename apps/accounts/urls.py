from django.urls import path
from django.urls import re_path
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.views.generic.base import TemplateView

from apps.accounts.admin_site import greenweb_admin as admin
from apps.accounts.views import (
    UserActivationView,
    UserRegistrationView,
    DashboardView,
    ProviderPortalHomeView,
    ProviderRequestDetailView,
    ProviderRequestWizardView,
    ProviderAutocompleteView,
    ProviderDomainsView,
    ProviderDomainCreateView,
    ProviderDomainDetailView,
    ProviderDomainDeleteView,
)

urlpatterns = [
    path(
        "",
        DashboardView.as_view(),
        name="dashboard",
    ),
    # auth pages
    path(
        "accounts/signup/",
        UserRegistrationView.as_view(template_name="auth/registration.html"),
        name="registration",
    ),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="auth/login.html"),
        name="login",
    ),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(template_name="auth/logout.html"),
        name="logout",
    ),
    re_path(
        r"accounts/activation/(?P<activation_key>[-:\w]+)/",
        UserActivationView.as_view(),
        name="activation",
    ),
    path(
        "accounts/password_reset/",
        auth_views.PasswordResetView.as_view(template_name="auth/password_reset.html"),
        name="password_reset",
    ),
    path(
        "accounts/password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="auth/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "accounts/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="auth/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "accounts/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="auth/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path(
        "accounts/password_change/",
        auth_views.PasswordChangeView.as_view(
            template_name="auth/password_change.html"
        ),
        name="password_change",
    ),
    path(
        "accounts/password_change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="auth/password_change_done.html"
        ),
        name="password_change_done",
    ),
    # override admin auth pages
    path("admin/login/", RedirectView.as_view(url="/accounts/login/")),
    path("admin/logout/", RedirectView.as_view(url="/accounts/logout/")),
    path("admin/activation/", RedirectView.as_view(url="/accounts/activation/")),
    path(
        "admin/password_reset/", RedirectView.as_view(url="/accounts/password_reset/")
    ),
    path(
        "admin/password_reset/done/",
        RedirectView.as_view(url="/accounts/password_reset/done/"),
    ),
    path(
        "admin/password_change/", RedirectView.as_view(url="/accounts/password_change/")
    ),
    path(
        "admin/password_change/done/",
        RedirectView.as_view(url="/accounts/password_change/done/"),
    ),
    # include admin URLs
    path("admin/", admin.urls),
    # custom views
    path(
        "provider-portal/",
        ProviderPortalHomeView.as_view(),
        name="provider_portal_home",
    ),
    path(
        "requests/<int:pk>/",
        ProviderRequestDetailView.as_view(),
        name="provider_request_detail",
    ),
    path(
        "requests/new/",
        ProviderRequestWizardView.as_view(ProviderRequestWizardView.FORMS),
        name="provider_registration",
    ),
    # For editing verification requests, we use the same view as for adding new ones
    # and pass instance_dict as a parameter to inject model instances to forms.
    # See more info: https://django-formtools.readthedocs.io/en/stable/wizard.html#formtools.wizard.views.WizardView.instance_dict
    path(
        "requests/<int:request_id>/edit/",
        lambda request, request_id: ProviderRequestWizardView.as_view(
            ProviderRequestWizardView.FORMS,
            instance_dict=ProviderRequestWizardView.get_instance_dict(request_id),
        )(request, request_id=request_id),
        name="provider_request_edit",
    ),
    # Editing a hosting provider re-uses a ProviderRequestWizardView with initial values
    # constructed form an existing Hostingprovider instance. Newly created ProviderRequest
    # will have Hostingprovider instance attached via FK, the approval process
    # should handle deciding whether to create a new Hostingprovider object or update existing one
    path(
        "providers/<int:provider_id>/edit/",
        lambda request, provider_id: ProviderRequestWizardView.as_view(
            ProviderRequestWizardView.FORMS,
            initial_dict=ProviderRequestWizardView.get_initial_dict(provider_id),
        )(request, provider_id=provider_id),
        name="provider_edit",
    ),
    path(
        "provider-autocomplete/",
        ProviderAutocompleteView.as_view(),
        name="provider-autocomplete",
    ),
    path(
        "before-starting/",
        TemplateView.as_view(template_name="provider_portal/before_starting.html"),
        name="before-starting",
    ),
    path(
        "providers/<int:provider_id>/domains/",
        ProviderDomainsView.as_view(),
        name="provider-domain-index",
    ),
    path(
        "providers/<int:provider_id>/domains/new",
        ProviderDomainCreateView.as_view(
            ProviderDomainCreateView.FORMS,
        ),
        name="provider-domain-create",
    ),
    path(
        "providers/<int:provider_id>/domains/<str:domain>",
        ProviderDomainDetailView.as_view(),
        name="provider-domain-detail",
    ),
    path(
        "providers/<int:provider_id>/domains/<str:domain>/delete",
        ProviderDomainDeleteView.as_view(),
        name="provider-domain-delete",
    ),
    path(
        "domain-claim/",
        ProviderPortalHomeView.as_view(),
        name="provider_domain_claim",
    ),
]
