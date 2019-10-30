from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone

from .hosting import Hostingprovider


class UserManager(BaseUserManager):
    pass


class User(AbstractBaseUser):
    algorithm = models.CharField(max_length=255)
    confirmation_token = models.CharField(max_length=255)
    credentials_expire_at = models.DateTimeField(null=True)
    credentials_expired = models.BooleanField()
    email = models.CharField(max_length=255)
    email_canonical = models.CharField(max_length=255)
    enabled = models.BooleanField()
    expired = models.BooleanField()
    expires_at = models.DateTimeField(null=True)

    # id_ge Green energy providers. Leave this for now.
    # old table, the idea might be resurrected.
    hostingprovider = models.ForeignKey(
        Hostingprovider, on_delete=models.CASCADE, db_column='id_hp'
    )
    last_login = models.DateTimeField(null=True)
    locked = models.BooleanField()
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
        'staff status',
        default=False,
        help_text='Designates whether the user can log into this admin site.',
    )
    is_active = models.BooleanField(
        'active',
        default=True,
        help_text=(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField('date joined', default=timezone.now)

    USERNAME_FIELD = 'username'
    objects = UserManager()

    class Meta:
        # managed = False
        db_table = 'fos_user'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['email_canonical']),
        ]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.username = self.username.lower()
        self.email = self.email.lower()
        super().save(args, **kwargs)
