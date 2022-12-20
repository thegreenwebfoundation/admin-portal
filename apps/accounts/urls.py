from django.urls import path, re_path
from django.contrib.auth import views as auth_views

from apps.accounts.views import (
    AdminActivationView,
    AdminRegistrationView,
    DashboardView,
    UserUpdateView,
    ProviderRequestListView,
    ProviderRequestDetailView,
    ProviderRegistrationView,
)

urlpatterns = [
    path(
        "",
        DashboardView.as_view(),
        name="dashboard",
    ),
    path(
        "password_reset/",
        auth_views.PasswordResetView.as_view(),
        name="admin_password_reset",
    ),
    path("registration/", AdminRegistrationView.as_view(), name="registration"),
    re_path(
        r"activation/(?P<activation_key>[-:\w]+)/",
        AdminActivationView.as_view(),
        name="activation",
    ),
    path(
        "password_change/",
        auth_views.PasswordChangeView.as_view(),
        name="password_change",
    ),
    path(
        "password_change/done/",
        auth_views.PasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("user/<pk>/", UserUpdateView.as_view(), name="user_edit"),
    path("requests/", ProviderRequestListView.as_view(), name="provider_request_list"),
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
]
