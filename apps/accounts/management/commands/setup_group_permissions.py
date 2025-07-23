from django.core.management.base import BaseCommand
from ...group_permissions import populate_group_permissions
from django.apps.registry import apps

class Command(BaseCommand):
    help = "Ensure all group_permissions are set correctly. To be run after all DB migrations."

    def handle(self, *args, **options):
        def logger(message):
            self.stdout.write(self.style.WARNING(message))
        populate_group_permissions(logger=logger)
        self.stdout.write(self.style.SUCCESS("Group permissions set!"))
