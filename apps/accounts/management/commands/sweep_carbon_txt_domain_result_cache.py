from django.core.management.base import BaseCommand
from sentry_sdk.crons import monitor
from apps.accounts.models import CarbonTxtDomainResultCache

class Command(BaseCommand):

    help = "Clear expired carbon.txt domain cache entries"



    # This is called by a cronjob which runs every hour at ten past the hour,
    # as specified in ansible/setup_cronjobs.yml in this repository.
    # Please note that when changing the cron schedule there, the "schedule" attribute
    # below should also be changed to match, otherwise we will receive spurious error
    # alerts in sentry.
    @monitor(monitor_slug="sweep_carbon_txt_domain_result_cache", monitor_config={ "schedule": "10 * * * *"})
    def handle(self, *args, **options):
        """
        Deletes all Carbon.txt domain result cache entries which were
        modified more than CARBON_TXT_CACHE_TTL seconds ago - set in an environment
        variable and defaulting to 24 hours.
        """
        CarbonTxtDomainResultCache.sweep_cache()

