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

# Environ
ROOT = environ.Path(__file__) - 3
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, os.getenv("SECRET_KEY")),
    DATABASE_URL=(str, os.getenv("DATABASE_URL")),
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
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 3rd party
    "anymail",
    "django_extensions",
    "django_mysql",
    "django_registration",
    "rest_framework",
    "rest_framework.authtoken",
    # project specific
    "apps.accounts",
    "apps.greencheck",
]

# Auth Mechanism
AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

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
    # 'extra': env.db('SQLITE_URL'),
}


# Password validation
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "apps.accounts.auth.LegacyBCrypt",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",},
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
STATIC_ROOT = ROOT("static")
STATIC_URL = "/static/"

# Media Files
MEDIA_ROOT = ROOT("media")
MEDIA_URL = "/media/"

# GCP BUCKET
PRESENTING_BUCKET = "presenting_bucket_staging"

RABBITMQ_URL = env("RABBITMQ_URL")


REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated",],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
}

DRAMATIQ_BROKER = {
    "BROKER": "dramatiq.brokers.rabbitmq.RabbitmqBroker",
    "OPTIONS": {"url": RABBITMQ_URL,},
    "MIDDLEWARE": [
        "dramatiq.middleware.Prometheus",
        "dramatiq.middleware.AgeLimit",
        "dramatiq.middleware.TimeLimit",
        "dramatiq.middleware.Callbacks",
        "dramatiq.middleware.Retries",
        "django_dramatiq.middleware.DbConnectionsMiddleware",
        "django_dramatiq.middleware.AdminMiddleware",
    ],
}


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "root": {"handlers": ["console"], "level": "DEBUG"},
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
