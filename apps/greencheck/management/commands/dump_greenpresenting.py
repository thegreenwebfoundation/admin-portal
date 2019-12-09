import subprocess
import os
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from sqlite_utils import Database
from google.cloud import storage


class Command(BaseCommand):
    help = "Dump green_presenting table into sqlite."

    def handle(self, *args, **options):
        root = Path(settings.ROOT)
        database_url = os.environ.get('DATABASE_URL')
        today = date.today()
        db_name = f'green_urls_{today}.db'
        bucket_name = settings.PRESENTING_BUCKET

        subprocess.run([
            'db-to-sqlite',
            database_url,
            db_name,
            '--table=green_presenting']
        )

        db = Database(db_name)
        presenting_table = db["green_presenting"]
        presenting_table.create_index(['url'])
        presenting_table.create_index(['hosted_by'])

        client = storage.Client()

        bucket_name = 'presenting_bucket_staging'
        bucket = client.get_bucket(bucket_name)
        blob = bucket.blob(db_name)
        blob.upload_from_filename(str(root / db_name))

