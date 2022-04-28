from .common import *  # noqa

INTERNAL_IPS = ["127.0.0.1"]
ALLOWED_HOSTS.extend(["127.0.0.1", "localhost"])  # noqa
DOMAIN_SNAPSHOT_BUCKET = "tgwf-green-domains-test"

AZURE_PROVIDER_ID = 123
# Fetch this from a bucket we control.
# TODO: Mock this out instead of making network requests, using pytest-mock
AZURE_IP_RANGE_JSON_FILE = "https://tgwf-web-app-test.s3.nl-ams.scw.cloud/data-imports/ms-azure-ip-ranges-2022-04-25.json"


# http://whitenoise.evans.io/en/stable/django.html#WHITENOISE_MANIFEST_STRICT
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# override settings, so we don't need to run rabbitmq in testing
# For more, see https://github.com/Bogdanp/django_dramatiq#testing
DRAMATIQ_BROKER = {
    "BROKER": "dramatiq.brokers.stub.StubBroker",
    "OPTIONS": {},
    "MIDDLEWARE": [
        # we don't collect these stats for tests
        # "dramatiq.middleware.Prometheus",
        "dramatiq.middleware.AgeLimit",
        "dramatiq.middleware.TimeLimit",
        "dramatiq.middleware.Callbacks",
        # we want to fail fast in most cases
        # "dramatiq.middleware.Retries",
    ],
}
