from django.conf import settings
from django.http import HttpRequest


def sentry_info(request: HttpRequest):
    """
    Add sentry configuration to the context in a HTTP request.

    This allows for the sentry config to be used in templates for
    frontend libraries.
    """

    # exit early if we don't have a sentry DSN set up
    try:
        sentry_dsn = settings.SENTRY_DSN
    except AttributeError:
        return {}

    return {
        "sentry": {
            "release": settings.SENTRY_RELEASE,
            "environment": settings.SENTRY_ENVIRONMENT,
            "dsn": settings.SENTRY_DSN,
        }
    }
