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
    "thegreenwebfoundation.org",
    "admin.thegreenwebfoundation.org",
    "newadmin.thegreenwebfoundation.org",
    "staging-admin.thegreenwebfoundation.org",
]


DOMAIN_SNAPSHOT_BUCKET = "tgwf-green-domains-live"

# report when things asplode
sentry_dsn = os.environ.get("SENTRY_DSN", False)  # noqa
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[DjangoIntegration()],
        # We assume that is a user is logged in, we want to be able
        # to see who is having a bad day, so we can contact them and
        # at least apologise about the broken site
        send_default_pii=True,
    )
