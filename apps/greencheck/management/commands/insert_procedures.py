from django.core.management.base import BaseCommand
from django.db import connection
from django.template.loader import render_to_string


class Command(BaseCommand):
    help = "Insert procedures."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            insert_urls = render_to_string('insert_url_procedure.sql')
            backfill = render_to_string('backfill_procedure.sql')
            presenting_table = render_to_string('presenting.sql')

            # add stored procedures to work by url, working backwards from
            # latest checks, rather than working forwards the earliest checks
            add_latest_check_for_url = render_to_string('add_latest_check_for_url_procedure.sql')
            backfill_by_url = render_to_string('backfill_by_url_procedure.sql')

            cursor.execute(presenting_table)
            cursor.execute(insert_urls)
            cursor.execute(backfill)


