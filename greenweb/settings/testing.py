import socket
from .common import * # noqa

import logging

from whitenoise.storage import CompressedManifestStaticFilesStorage

logger = logging.getLogger(__name__)

INTERNAL_IPS = ['127.0.0.1']
ALLOWED_HOSTS.extend(['127.0.0.1', 'localhost'])


# In testing, using whitenoise here doesn't really help us, so we
# switch back to the default instead.
# This is recommended by Django maintainers, and referred to in
# the whitenoise docs
# https://docs.djangoproject.com/en/3.0/ref/contrib/staticfiles/#django.contrib.staticfiles.storage.ManifestStaticFilesStorage.manifest_strict
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
