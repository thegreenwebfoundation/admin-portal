from .common import *  # noqa

INTERNAL_IPS = ["127.0.0.1"]
ALLOWED_HOSTS.extend(["127.0.0.1", "localhost"])  # noqa
DOMAIN_SNAPSHOT_BUCKET = "tgwf-green-domains-test"


# override settings, so we don't need to run rabbitmq in testing
# For more, see https://github.com/Bogdanp/django_dramatiq#testing
DRAMATIQ_BROKER["BROKER"] = "dramatiq.brokers.stub.StubBroker"  # noqa
DRAMATIQ_BROKER["OPTIONS"] = {}  # noqa

# Defines which database should be used to persist Task objects when the
# AdminMiddleware is enabled.  The default value is "default".
DRAMATIQ_TASKS_DATABASE = "default"
