import socket
from .common import * # noqa

DEBUG = True
INTERNAL_IPS = ['127.0.0.1']
hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
INTERNAL_IPS += [ip[:-1] + '1' for ip in ips]
ALLOWED_HOSTS.extend(['127.0.0.1', 'localhost'])

INSTALLED_APPS.append('debug_toolbar')

# Insert debug_toolbar middleware as first element
# Warning at: https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#middleware
MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
