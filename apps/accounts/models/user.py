from django.contrib.auth.models import (
    AbstractBaseUser,
    UserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone
from django.core.mail import send_mail

from .hosting import Hostingprovider


class User(AbstractBaseUser, PermissionsMixin):
    algorithm = models.CharField(max_length=255)
    confirmation_token = models.CharField(max_length=255)
    credentials_expire_at = models.DateTimeField(null=True)
    credentials_expired = models.BooleanField(default=False)
    email = models.CharField(max_length=255)
    email_canonical = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)
    expired = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True)

    # id_ge Green energy providers. Leave this for now.
    # old table, the idea might be resurrected.
    hostingprovider = models.ForeignKey(
        Hostingprovider, on_delete=models.CASCADE, db_column='id_hp', unique=True
    )
    last_login = models.DateTimeField(null=True)
    locked = models.BooleanField(default=False)
    password = models.CharField('password', max_length=128, db_column='django_password')
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
    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']
    objects = UserManager()

    class Meta:
        # managed = False
        db_table = 'fos_user'
        indexes = [
            models.Index(fields=['username'], name='username'),
            models.Index(fields=['email'], name='email'),
            models.Index(fields=['email_canonical'], name='email_canonical'),
        ]

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        self.username = self.username.lower()
        self.username_canonical = self.username.lower()
        self.email_canonical = self.email
        self.email = self.email.lower()
        super().save(args, **kwargs)

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)

