from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection

from django.conf import settings

BASE_PATH = Path(settings.ROOT)


class Command(BaseCommand):
    help = "Insert procedures."

    def read(self, filename):
        PATH = BASE_PATH / 'apps' / 'greencheck' / 'templates' / filename
        return PATH.open().read()

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            insert_urls = self.read('insert_url_procedure.sql')
            backfill = self.read('backfill_procedure.sql')

            cursor.execute(insert_urls)
            cursor.execute(backfill)
