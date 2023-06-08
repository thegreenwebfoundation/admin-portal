import datetime

from django.contrib.auth.models import (
    AbstractBaseUser,
    UserManager,
    PermissionsMixin,
)

from django.db import models
from django.core.mail import send_mail
from django.urls import reverse
from guardian.mixins import GuardianUserMixin
from guardian.shortcuts import get_objects_for_user

from ..permissions import manage_provider, manage_datacenter
from .hosting import Hostingprovider


class User(AbstractBaseUser, PermissionsMixin, GuardianUserMixin):
    algorithm = models.CharField(max_length=255)
    confirmation_token = models.CharField(max_length=255)
    credentials_expire_at = models.DateTimeField(null=True)
    credentials_expired = models.BooleanField(default=False)
    email = models.CharField(max_length=255)
    email_canonical = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)
    expired = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True)
    last_login = models.DateTimeField(null=True)
    locked = models.BooleanField(default=False)
    password = models.CharField("password", max_length=128, db_column="django_password")
    legacy_password = models.CharField(
        "legacy_password", max_length=128, db_column="password"
    )
    # password already provided in abstract base user.
    password_requested_at = models.DateTimeField(null=True)
    # contains a php array, needs to be deserialized with something like in this
    # gist
    # https://gist.github.com/sj26/292552
    roles = models.TextField()
    salt = models.CharField(max_length=255)
    type = models.CharField(max_length=15)
    username = models.CharField(max_length=255, unique=True)
    username_canonical = models.CharField(max_length=255)

    is_staff = models.BooleanField(
        "staff status",
        default=False,
        help_text="Designates whether the user can log into this admin site.",
    )
    is_active = models.BooleanField(
        "active",
        default=True,
        help_text=(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    date_joined = models.DateTimeField("date joined", default=datetime.datetime.now)
    EMAIL_FIELD = "email"
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]
    objects = UserManager()

    class Meta:
        # managed = False
        db_table = "fos_user"
        indexes = [
            models.Index(fields=["email"], name="email"),
            models.Index(fields=["email_canonical"], name="email_canonical"),
        ]

    # Properties

    def __str__(self):
        return self.username

    @property
    def is_admin(self):
        return self.groups.filter(name="admin").exists()

    @property
    def hosting_providers(self) -> models.QuerySet[Hostingprovider]:
        """
        Returns a QuerySet of all Hostingproviders that the User has permissions to manage
        """
        return get_objects_for_user(self, str(manage_provider))

    @property
    def data_centers(self) -> models.QuerySet[Hostingprovider]:
        """
        Returns a QuerySet of all Datacenters that the User has permissions to manage
        """
        return get_objects_for_user(self, str(manage_datacenter))

    def get_absolute_url(self):
        return reverse("user_edit", args=[str(self.id)])

    def save(self, *args, **kwargs):
        self.username = self.username.lower()
        self.username_canonical = self.username.lower()
        self.email_canonical = self.email
        self.email = self.email.lower()

        # we need this to maintain capatibility with the legacy admin
        # system, which still looks for the `password` column on the
        # fos_user table
        self.legacy_password = self.password
        super().save(*args, **kwargs)

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)

    @property
    def admin_url(self):
        return reverse(
            f"greenweb_admin:{self._meta.app_label}_{self._meta.model_name}_change",
            args=(self.pk,),
        )
