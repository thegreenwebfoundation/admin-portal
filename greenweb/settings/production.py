from .common import * # noqa


ANYMAIL = {
    'MAILGUN_API_KEY': env('MAILGUN_API_KEY'),
}
EMAIL_BACKEND = 'anymail.backends.mailgun.EmailBackend'

ALLOWED_HOSTS = ['thegreenwebfoundation.org', 'newadmin.thegreenwebfoundation.org']
