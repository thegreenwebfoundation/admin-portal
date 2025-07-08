import csv
from django.core.management.base import BaseCommand
from django.utils import timezone

from ...models import Hostingprovider


class Command(BaseCommand):
    help = "Create a CSV file of providers and expiry dates for evidence"

    def handle(self, *args, **options):
        providers_and_expiry_dates = [
            (hp.id, hp.name, hp.evidence_expiry_date, hp.is_listed)
            for hp in Hostingprovider.objects.filter(archived=False)
        ]

        today = timezone.now().date()
        today_string = today.strftime("%Y-%m-%d")

        with open(f"providers_and_expiry_dates_{today_string}.csv", "w") as csv_file:
            fieldnames = ["id", "name", "expiry_date", "visible on website"]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for row in providers_and_expiry_dates:
                writer.writerow(
                    {
                        "id": row[0],
                        "name": row[1],
                        "expiry_date": row[2],
                        "visible on website": row[3],
                    }
                )
