from django.urls import path
from django.conf.urls import url
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView

from apps.accounts.admin_site import greenweb_admin as admin
from apps.accounts.views import (
    UserActivationView,
    UserRegistrationView,
    DashboardView,
    UserUpdateView,
    ProviderPortalHomeView,
    ProviderRequestDetailView,
    ProviderRegistrationView,
    ProviderAutocompleteView,
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
    url(
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
    path("user/<pk>/", UserUpdateView.as_view(), name="user_edit"),
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
        ProviderRegistrationView.as_view(ProviderRegistrationView.FORMS),
        name="provider_registration",
    ),
    path(
        "provider-autocomplete/",
        ProviderAutocompleteView.as_view(),
        name="provider-autocomplete",
    ),
]
