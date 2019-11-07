from django.core.management.base import BaseCommand
from apps.accounts.models import User


class Command(BaseCommand):
    help = "My shiny new management command."

    def handle(self, *args, **options):
        valid_users = User.objects.raw("""
            SELECT u.id, u.email, u.id_hp from fos_user as u
            JOIN datacenters as dc on dc.user_id = u.id
            UNION
            SELECT u.id, u.email, u.id_hp from fos_user as u
            JOIN hostingproviders as hp on hp.id = u.id_hp
        """)

        invalid_users = User.objects.exclude(id__in=[u.pk for u in valid_users])
        print('Number of invalid users: ', invalid_users.count())
        invalid_users.delete()
        print('Invalid users deleted')
