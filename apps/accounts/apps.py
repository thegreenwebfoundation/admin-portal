from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.accounts"

    def ready(self):
        # Patch AnonymousUser so that code accessing `request.user.is_admin`
        # does not raise AttributeError for unauthenticated users.
        from django.contrib.auth.models import AnonymousUser

        AnonymousUser.is_admin = property(lambda self: False)
