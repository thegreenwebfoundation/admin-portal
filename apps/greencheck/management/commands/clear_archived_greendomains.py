from django.core.management.base import BaseCommand

from apps.accounts.models import Hostingprovider
from ...models import GreenDomain


class Command(BaseCommand):
    help = "Clear cached GreenDomain records for providers that are archived)"

    def handle(self, *args, **options) -> None:
        providers = Hostingprovider.objects.filter(archived=True).all()
        provider_ids = [p.id for p in providers]
        query_set=GreenDomain.objects.filter(hosted_by_id__in=provider_ids)
        provider_count = len(providers)
        domain_count = query_set.count()
        query_set.delete()
        self.stdout.write(
            f"Cache clear complete: Deleted {domain_count} green domains for {provider_count} archived providers."
        )
