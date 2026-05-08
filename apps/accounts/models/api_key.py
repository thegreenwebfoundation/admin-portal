from django.conf import settings
from django.db import models
from django.utils import timezone
from rest_framework_api_key.models import AbstractAPIKey, BaseAPIKeyManager

class APIKeyManager(BaseAPIKeyManager):

    def get_usable_keys(self):
        return self.filter(
            models.Q(revoked=False),
            models.Q(expiry_date__isnull=True) | models.Q(expiry_date__gt=timezone.now())
        )

    def create_key_for_user(self, user, note="", expiry_date=None):
        if self.get_usable_keys().filter(user=user).count() >= settings.MAX_API_KEYS_PER_USER:
            raise ValueError("Only 3 active API keys allowed per account.")

        return self.create_key(user=user, note=note, expiry_date=expiry_date)

class APIKey(AbstractAPIKey):

    name = None # Overrides the field set in the superclass.

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    note = models.CharField(max_length=255, blank=True)
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
    def name(self):
        return f"{self.user.username}:{self.prefix}"
