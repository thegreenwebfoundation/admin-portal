from .common import *  # noqa
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration


ANYMAIL = {
    "MAILGUN_API_KEY": env("MAILGUN_API_KEY"),  # noqa
    "MAILGUN_SENDER_DOMAIN": "mg.thegreenwebfoundation.org",
    "MAILGUN_API_URL": "https://api.eu.mailgun.net/v3",
}
EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"

ALLOWED_HOSTS = [
    "localhost",
    # accept any address ending with .thegreenwebfoundation.org
    # for more see the docs about setting a subdomain wildcard
    # https://docs.djangoproject.com/en/4.1/ref/settings/#std-setting-ALLOWED_HOSTS
    ".thegreenwebfoundation.org",
    # accept any address ending with .greenweb.org too
    ".greenweb.org",
]


DOMAIN_SNAPSHOT_BUCKET = "tgwf-green-domains-live"
# Used by django storages for storing files
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Scaleway deets
AWS_ACCESS_KEY_ID = env("OBJECT_STORAGE_ACCESS_KEY_ID")  # noqa
AWS_SECRET_ACCESS_KEY = env("OBJECT_STORAGE_SECRET_ACCESS_KEY")  # noqa
AWS_STORAGE_BUCKET_NAME = env("OBJECT_STORAGE_BUCKET_NAME")  # noqa
AWS_S3_REGION_NAME = env("OBJECT_STORAGE_REGION")  # noqa
AWS_S3_ENDPOINT_URL = env("OBJECT_STORAGE_ENDPOINT")  # noqa
# do not overwrite files (upload files with the same name as separate files)
AWS_S3_FILE_OVERWRITE = False

# report when things asplode
SENTRY_DSN = os.environ.get("SENTRY_DSN", False)  # noqa
SENTRY_ENVIRONMENT = os.environ.get("SENTRY_ENVIRONMENT", "production")  # noqa
SENTRY_RELEASE = os.environ.get("SENTRY_RELEASE", "provider-portal@1.4.x")  # noqa

# Set to a value between 0 for 0% of request and
# 1.0 to capture 100% of requests and annotate
# them with traces for performance monitoring.
# This generates *a lot* of data, so its better to
# sample at a lower value, or only activate this
# on specific environments

# For more:
# https://docs.sentry.io/platforms/python/guides/django/
# https://docs.sentry.io/platforms/python/guides/django/performance/
sentry_sample_rate = os.environ.get("SENTRY_SAMPLE_RATE", 0)  # noqa


def filter_sentry(event, hint):
    """
    Filter out noisy errors from pika, the underlying 
    rabbitmq library that we know are caught by Dramatiq and retried
    """

    if 'logger' in event and event['logger'] in [
        'pika.adapters.blocking_connection',
        'pika.adapters.base_connection',
        'pika.adapters.utils.io_services_utils'
    ]:
        return None

    return event


if SENTRY_DSN:
    sentry_sdk.init(
        # set our identifying credentials
        dsn=SENTRY_DSN,
        release=SENTRY_RELEASE,
        environment=SENTRY_ENVIRONMENT,
        # Set traces_sample_rate.
        traces_sample_rate=float(sentry_sample_rate),
        # activate the django specific integrations for sentry
        integrations=[DjangoIntegration()],
        # We assume that is a user is logged in, we want to be able
        # to see who is having a bad day, so we can contact them and
        # at least apologise about the broken site
        send_default_pii=True,
        before_send=filter_sentry,
    )


# Tell Django to look for the `HTTP_X_FORWARDED_PROTO` header, and if it sees it
# assume that this was a secure request. Without this, Django sees a mismatch
# between:
# 1. the request coming in over HTTPS to Caddy, the reverse proxy in front of Django,
# 2 -the request coming in over HTTP to Django, because Caddy is proxying over http
# 'HTTP_X_FORWARDED_PROTO' is the name of the header that Caddy passes along, that we look for.
# See more:
# https://noumenal.es/notes/til/django/csrf-trusted-origins/
# https://stackoverflow.com/questions/72584282/django-caddy-csrf-protection-issues
# https://docs.djangoproject.com/en/4.2/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
