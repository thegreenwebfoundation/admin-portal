import socket
from .common import *  # noqa

DEBUG = True
INTERNAL_IPS = ["127.0.0.1"]
hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
INTERNAL_IPS += [ip[:-1] + "1" for ip in ips]

# we add gitpod.io to support their ephemeral dev environments
# add others as we need them
ALLOWED_HOSTS.extend(["127.0.0.1", "localhost", ".gitpod.io"])  # noqa

INSTALLED_APPS.append("debug_toolbar")  # noqa

INSTALLED_APPS.append("django_browser_reload")  # noqa

INSTALLED_APPS.insert(0, "whitenoise.runserver_nostatic")  # noqa

# this snippet allows us to see the hierarchy of templates used to render a page
# without it DEBUG_TOOLBAR runs out of "cache slots", and shows a message saying:

# "Data for this panel isn't available anymore. Please reload the page and retry."

# For more, see:
# https://timonweb.com/django/fixing-the-data-for-this-panel-isnt-available-anymore-error-in-django-debug-toolbar/
if DEBUG:
    hide_toolbar_patterns = ["/media/", "/static/"]

    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda request: not any(
            request.path.startswith(p) for p in hide_toolbar_patterns
        ),
    }


# Insert debug_toolbar middleware as first element
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#middleware
MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa


MIDDLEWARE.append(
    "django_browser_reload.middleware.BrowserReloadMiddleware",
)  # noqa


EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# mailhog
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "localhost"
EMAIL_PORT = 1025
SITE_URL = "http://localhost:9000"

MEDIA_ROOT = ROOT("media")
MEDIA_URL = "/media/"
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

DOMAIN_SNAPSHOT_BUCKET = "tgwf-green-domains-test"
