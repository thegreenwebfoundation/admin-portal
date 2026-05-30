from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Create trigger to insert urls."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                -- CREATE TRIGGER "after_greencheck_insert" ---------------
                CREATE TRIGGER after_greencheck_insert
                    AFTER INSERT ON greencheck
                    FOR EACH ROW
                CALL insert_urls(NEW.url, NEW.green, NEW.id_hp, NEW.datum);
                -- --------------------------------------------------------
            """
            )
