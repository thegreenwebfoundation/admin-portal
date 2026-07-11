from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Initial migration."

    def handle(self, *args, **options):
        call_command("migrate", "contenttypes")
        call_command("migrate", "auth")
        call_command("migrate", "--fake-initial", "accounts", "0001_initial")
        call_command("migrate", "accounts")
        call_command("migrate", "admin")
        call_command("migrate", "--fake", "greencheck", "0001_initial")
        call_command("migrate", "sessions")
        call_command("migrate")
        self.stdout.write(self.style.SUCCESS("Initial migration completed!"))
