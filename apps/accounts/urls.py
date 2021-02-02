from django.urls import path
from django.conf.urls import url
from django.contrib.auth import views as auth_views

from apps.accounts.views import AdminRegistrationView
from apps.accounts.views import AdminActivationView

urlpatterns = []

urlpatterns = [
    path(
        "password_reset/",
        auth_views.PasswordResetView.as_view(),
        name="admin_password_reset",
    ),
    path("registration/", AdminRegistrationView.as_view(), name="registration"),
    url(
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
]
