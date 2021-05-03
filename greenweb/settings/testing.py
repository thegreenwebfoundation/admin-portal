from .common import *  # noqa

INTERNAL_IPS = ["127.0.0.1"]
ALLOWED_HOSTS.extend(["127.0.0.1", "localhost"])  # noqa
DOMAIN_SNAPSHOT_BUCKET = "tgwf-green-domains-test"


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
