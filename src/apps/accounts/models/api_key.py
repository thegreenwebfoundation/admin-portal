import re
from django.conf import settings
from django.db import models
from django.utils import timezone
from rest_framework_api_key.models import AbstractAPIKey, BaseAPIKeyManager



class APIKeyManager(BaseAPIKeyManager):

    def get_usable_keys(self):
        return self.filter(
            models.Q(revoked=False),
            models.Q(expiry_date__isnull=True) | models.Q(expiry_date__gt=timezone.now()),
            models.Q(user__api_access_banned=False)
        )

    def create_key_for_user(self, user, service, motivation, note="", expiry_date=None):
        if self.get_usable_keys().filter(user=user).count() >= user.api_key_limit:
            raise ValueError(f"Only {user.api_key_limit} active API keys allowed for this account.")

        return self.create_key(user=user, motivation=motivation, service=service, note=note, expiry_date=expiry_date)

    def create_key(self, **kwargs):
        instance, key = super().create_key(**kwargs)
        return instance, f"{settings.API_KEY_PREFIX}_{key}"

    def get_from_key(self, key: str):
        if key.startswith(settings.API_KEY_PREFIX):
            key = re.sub(f"^{settings.API_KEY_PREFIX}_", "", key)
        return super().get_from_key(key)


class APIKeyPrivilegeLevel(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False)
    note = models.CharField(max_length=512, blank=True)

    def __str__(self):
        return self.name

class APIService(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False)
    key = models.CharField(max_length=255, null=False, blank=False)
    documentation_url = models.URLField(null=False, blank=False)
    api_url = models.URLField(null=False, blank=False)

    def __str__(self):
        return f"{self.name} ({self.key})"


class APIKey(AbstractAPIKey):

    name = None # Overrides the field set in the superclass.

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    note = models.CharField(max_length=255, blank=True)
    motivation = models.TextField(null=False, blank=False)

    service = models.ForeignKey(
       APIService,
       on_delete=models.CASCADE,
       null=False, blank=False
    )

    privilege_level = models.ForeignKey(
        APIKeyPrivilegeLevel,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    objects = APIKeyManager()

    class Meta(AbstractAPIKey.Meta):
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
        indexes = [
            models.Index(fields=["prefix", "hashed_key"]),
            models.Index(fields=["revoked", "expiry_date"]),
            models.Index(fields=["user"]),
        ]

    @property
    def displayable_prefix(self):
        return f"{settings.API_KEY_PREFIX}_{self.prefix}"

    @property
    def name(self):
        return f"{self.user.username}:{self.displayable_prefix}"
