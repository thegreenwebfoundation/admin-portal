"""
Django settings for Greenweb foundation project.

Generated by 'django-admin startproject' using Django.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

import os
import environ
import pathlib
from dramatiq import middleware as dramatiq_middleware

# Environ
ROOT = environ.Path(__file__) - 3
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, os.getenv("SECRET_KEY")),
    DATABASE_URL=(str, os.getenv("DATABASE_URL")),
    DATABASE_URL_READ_ONLY=(str, os.getenv("DATABASE_URL_READ_ONLY")),
    DOMAIN_SNAPSHOT_BUCKET=(str, os.getenv("DOMAIN_SNAPSHOT_BUCKET")),
    # add for object storage
    OBJECT_STORAGE_ENDPOINT=(str, os.getenv("OBJECT_STORAGE_ENDPOINT")),
    OBJECT_STORAGE_REGION=(str, os.getenv("OBJECT_STORAGE_REGION")),
    OBJECT_STORAGE_ACCESS_KEY_ID=(str, os.getenv("OBJECT_STORAGE_ACCESS_KEY_ID")),
    OBJECT_STORAGE_SECRET_ACCESS_KEY=(
        str,
        os.getenv("OBJECT_STORAGE_SECRET_ACCESS_KEY"),
    ),
    REDIS_HOST=(str, "localhost"),
    BASICAUTH_DISABLE=(bool, True),
    BASICAUTH_PASSWORD=(str, "strong_password"),
)

environ.Env.read_env(".env")  # Read .env

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/dev/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ["thegreenwebfoundation.org"]


# Setting for django-registration
ACCOUNT_ACTIVATION_DAYS = 7  # One-week activation window

# Application definition
INSTALLED_APPS = [
    "django_dramatiq",
    # these need to go before django contrib, as described in the below docs
    # for DAL
    # https://django-autocomplete-light.readthedocs.io/en/master/install.html
    "dal",
    "dal_select2",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # 3rd party
    "logentry_admin",
    "anymail",
    "django_extensions",
    "django_mysql",
    "django_registration",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_yasg",
    "corsheaders",
    "taggit",
    "taggit_labels",
    "taggit_serializer",
    "waffle",
    "django_filters",
    "django_admin_multiple_choice_list_filter",
    "formtools",
    "convenient_formsets",
    # UI
    "tailwind",
    "crispy_forms",
    "crispy_tailwind",
    "widget_tweaks",
    # analysis
    "explorer",
    # project specific
    "apps.theme",
    "apps.accounts",
    "apps.greencheck",
]

TAILWIND_APP_NAME = "apps.theme"
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"


# Auth Mechanism
AUTH_USER_MODEL = "accounts.User"

LOGIN_REDIRECT_URL = "/"

# We need this to account for some providers that have numbers of IP
# ranges that are greater than the default limit in django.
# By setting this to None, we no longer check for the size of the form.
# This is not ideal, but it at least means some hosting providers can
# update their info while we rethink how people update IP range info.
# https://docs.djangoproject.com/en/4.0/ref/settings/#data-upload-max-number-fields
DATA_UPLOAD_MAX_NUMBER_FIELDS = None

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "waffle.middleware.WaffleMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # see the section below on BASICAUTH
    "basicauth.middleware.BasicAuthMiddleware",
]

# Basic auth for staging
# we include it, but leave it disabled,
# except on staging environments
# https://pypi.org/project/django-basicauth/
BASICAUTH_DISABLE = env("BASICAUTH_DISABLE")
BASICAUTH_USERS = {"staging_user": env("BASICAUTH_PASSWORD")}


ROOT_URLCONF = "greenweb.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "greenweb.wsgi.application"


# Because our greencheck tables use TIMESTAMP, we can't use timezone aware dates
# https://docs.djangoproject.com/en/3.1/ref/databases/#timestamp-columns
USE_TZ = False

# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    "default": env.db(),
    "read_only": env.db_url("DATABASE_URL_READ_ONLY"),
}
EXPLORER_CONNECTIONS = {"Default": "read_only"}
EXPLORER_DEFAULT_CONNECTION = "read_only"
EXPLORER_AUTORUN_QUERY_WITH_PARAMS = False
EXPLORER_PERMISSION_VIEW = lambda r: r.user.is_admin
EXPLORER_PERMISSION_CHANGE = lambda r: r.user.is_admin

# only support API access with the sql explorer if we
# explicitly set the token
EXPLORER_TOKEN = os.getenv("EXPLORER_TOKEN")
if EXPLORER_TOKEN:
    EXPLORER_TOKEN_AUTH_ENABLED = True

# Geo IP database
GEOIP_PATH = pathlib.Path(ROOT) / "data" / "GeoLite2-City.mmdb"

# Allow requests from any origin, but only make the API urls available
# CORS_URLS_REGEX = r"^/api/.*$"
CORS_ALLOW_ALL_ORIGINS = True


# Password validation
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "apps.accounts.auth.LegacyBCrypt",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (  # noqa
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        ),
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True

# Email settings
DEFAULT_FROM_EMAIL = "support@thegreenwebfoundation.org"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATIC_URL = "/static/"

STATICFILES_DIRS = [
    "apps/theme/static",
]


# staticfiles it the name of the directory we collate files,
# so we can follow the convention of using static *inside django apps*
# for files we can to pick up with `collectstatic` commands.
STATIC_ROOT = ROOT("staticfiles")


# Media Files
MEDIA_ROOT = ROOT("media")
MEDIA_URL = "/media/"

# OBJECT STORAGE BUCKET
DOMAIN_SNAPSHOT_BUCKET = env("DOMAIN_SNAPSHOT_BUCKET")
OBJECT_STORAGE_ENDPOINT = env("OBJECT_STORAGE_ENDPOINT")
OBJECT_STORAGE_REGION = env("OBJECT_STORAGE_REGION")
OBJECT_STORAGE_ACCESS_KEY_ID = env("OBJECT_STORAGE_ACCESS_KEY_ID")
OBJECT_STORAGE_SECRET_ACCESS_KEY = env("OBJECT_STORAGE_SECRET_ACCESS_KEY")

# Importer variables
# Microsoft
MICROSOFT_PROVIDER_ID = env("MICROSOFT_PROVIDER_ID")
MICROSOFT_LOCAL_FILE_DIRECTORY = env("MICROSOFT_LOCAL_FILE_DIRECTORY")

# Equinix
EQUINIX_PROVIDER_ID = env("EQUINIX_PROVIDER_ID")
EQUINIX_REMOTE_API_ENDPOINT = env("EQUINIX_REMOTE_API_ENDPOINT")

# Amazon
AMAZON_PROVIDER_ID = env("AMAZON_PROVIDER_ID")
AMAZON_REMOTE_API_ENDPOINT = env("AMAZON_REMOTE_API_ENDPOINT")

RABBITMQ_URL = env("RABBITMQ_URL")

# Redis
REDIS_HOST = env("REDIS_HOST")

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
}


DRAMATIQ_BROKER = {
    "BROKER": "dramatiq.brokers.rabbitmq.RabbitmqBroker",
    "OPTIONS": {
        "url": RABBITMQ_URL,
    },  # noqa
    "MIDDLEWARE": [
        # remove until we are actually using it
        # "dramatiq.middleware.Prometheus"
        "dramatiq.middleware.AgeLimit",
        # use a longer timeout, as the default of 10 minutes means
        # that long running queries are aborted too early
        dramatiq_middleware.TimeLimit(time_limit=60 * 60 * 1000),
        "dramatiq.middleware.Callbacks",
        "dramatiq.middleware.Retries",
    ],
}

# For some jobs, we want workers dedicated to that queue only
# this is where we list them.
DRAMATIQ_EXTRA_QUEUES = {"stats": "stats"}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "root": {"handlers": ["console"], "level": "INFO"},
    "handlers": {
        "console": {
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            "datefmt": "%d/%b/%Y %H:%M:%S",
        },
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "loggers": {
        "django.db.backends": {
            # uncomment to see all queries
            # 'level': 'DEBUG',
            "handlers": ["console"],
        }
    },
}

SITE_URL = "https://admin.thegreenwebfoundation.org"


GOOGLE_PROVIDER_ID = 2345
GOOGLE_DATASET_ENDPOINT = "https://www.gstatic.com/ipranges/cloud.json"

TAGGIT_CASE_INSENSITIVE = True

INTERNAL_IPS = [
    "127.0.0.1",
]
