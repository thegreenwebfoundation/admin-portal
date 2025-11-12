import datetime

from django.core.management.base import BaseCommand
from sentry_sdk.crons import monitor

from apps.accounts.models import Hostingprovider
from ...models import GreenDomain, GreenDomainBadge


class Command(BaseCommand):

    TIME_TO_LIVE_DAYS = 365

    help = "Clear expired GreenDomain records"


    def _clear_archived_provider_domains(self):
        """
        Clears all domains associated with archived providers, which should no
        longer show as green.
        """
        providers = Hostingprovider.objects.filter(archived=True).all()
        provider_ids = [p.id for p in providers]
        query_set=GreenDomain.objects.filter(hosted_by_id__in=provider_ids)
        provider_count = len(providers)
        domain_count = query_set.count()
        for green_domain in query_set:
            GreenDomainBadge.clear_cache(green_domain.url)
        query_set.delete()
        self.stdout.write(
            f"Cleared archived providers: Deleted {domain_count} green domains for {provider_count} archived providers."
        )


    def _clear_expired_domains(self):
        """
        Clears all domains created more than TIME_TO_LIVE_DAYS days ago
        """
        cutoff_date = (
                datetime.datetime.now() - datetime.timedelta(days=self.TIME_TO_LIVE_DAYS)
        ).replace(hour=0, minute=0, second=0, microsecond=0)
        query_set = GreenDomain.objects.filter(created__lte=cutoff_date)
        domain_count = query_set.count()
        for green_domain in query_set:
            GreenDomainBadge.clear_cache(green_domain.url)
        query_set.delete()
        cutoff_date_string = cutoff_date.isoformat()
        self.stdout.write(
            f"Cleared expired domains: Deleted {domain_count} green domains created before {cutoff_date_string}."
        )

    def _clear_expired_badges(self):
        """
        Clears all green web badge image caches created more than TIME_TO_LIVE_DAYS days ago
        """
        cutoff_date = (
                datetime.datetime.now() - datetime.timedelta(days=self.TIME_TO_LIVE_DAYS)
        ).replace(hour=0, minute=0, second=0, microsecond=0)
        query_set = GreenDomainBadge.objects.filter(created__lte=cutoff_date)
        badge_count = query_set.count()
        query_set.delete()
        cutoff_date_string = cutoff_date.isoformat()
        self.stdout.write(
            f"Cleared expired greenweb badges: Deleted {badge_count} badge images created before {cutoff_date_string}."
        )

    # This is called by a cronjob which runs at 1AM every day, as specified in
    # ansible/setup_cronjobs.yml in this repository.
    # Please note that when changing the cron schedule there, the "schedule" attribute
    # below should also be changed to match, otherwise we will receive spurious error
    # alerts in sentry.
    @monitor(monitor_slug="clear_expired_domains", monitor_config={ "schedule": "0 1 * * *" })
    def handle(self, *args, **options) -> None:
        self._clear_archived_provider_domains()
        self._clear_expired_domains()
        self._clear_expired_badges()
