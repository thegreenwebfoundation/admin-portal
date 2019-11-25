from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.mail import send_mass_mail
from django.template.loader import render_to_string

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Send out migration email to all users."

    def handle(self, *args, **options):
        emails = User.objects.all().values_list('email', flat=True)

        email_message = render_to_string('emails/migration_email.txt', context={})
        messages = [
            (
                'Please reset your password at Green web foundation',
                email_message, settings.DEFAULT_FROM_EMAIL, [email]
            )
            for email in emails
        ]
        send_mass_mail(messages)
