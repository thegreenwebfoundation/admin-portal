from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Migrating 0 to null for ip approvals"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE greencheck_ip_approve
                SET idorig = NULL
                WHERE idorig = 0
            """
            )

            cursor.execute(
                """
                UPDATE greencheck_as_approve
                SET idorig = NULL
                WHERE idorig = 0
            """
            )

        self.stdout.write(self.style.SUCCESS("Migrated 0 to be NULL!"))
