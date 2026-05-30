from .production import *  # noqa

# the only change compared to production is
# the bucket we use. the rest is set in env vars
# TODO consider moving this to env vars too
DOMAIN_SNAPSHOT_BUCKET = "tgwf-green-domains-staging"

# the other change we make for staging is to add middleware
# that puts any dynamic request behind a HTTP Basic Auth.
# See more: https://pypi.org/project/django-basicauth/
MIDDLEWARE.append("basicauth.middleware.BasicAuthMiddleware")
