from .common import * # noqa


ANYMAIL = {
    'MAILGUN_API_KEY': env('MAILGUN_API_KEY'),
    'MAILGUN_SENDER_DOMAIN': 'mg.thegreenwebfoundation.org',
    'MAILGUN_API_URL': 'https://api.eu.mailgun.net/v3'
}
EMAIL_BACKEND = 'anymail.backends.mailgun.EmailBackend'

ALLOWED_HOSTS = [
    'localhost',
    'thegreenwebfoundation.org',
    'admin.thegreenwebfoundation.org',
    'newadmin.thegreenwebfoundation.org',
    'staging-admin.thegreenwebfoundation.org',
]

# bucket name in GCP
PRESENTING_BUCKET = 'presenting_bucket_production'
