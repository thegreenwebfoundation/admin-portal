import logging
from apps.greencheck.models import Greencheck, GreenPresenting, TopUrl, Hostingprovider

from django.core.management.base import BaseCommand
from django.db import connection
import datetime
import warnings
logger = logging.getLogger(__name__)

# Silence the runtime warnings about naive datetimes. Because we're using two systems,
#  api and admin-portal, we need to check how both frameworks handle this first
warnings.filterwarnings("ignore", category=RuntimeWarning)

GREEN = 1

class TopUrlUpdater:

    def update_green_domains(self, queryset):
        """
        Accepts a queryset of objects with a 'url' property, and iterates through the
        list of domains, updating the Green Presenting table, with the date of the latest
        check.
        """
        count = 0
        new_domains = 0
        updated_domains = 0

        for domain in queryset.iterator():

            count += 1

            # every 10000 domains processed, log the progress
            if count % 10_000 == 0:
                now = datetime.datetime.now().strftime("%Y-%m-%d - %H-%M-%S")
                logger.info(f"Processed: {count} domains so far. Time: {now}")

            try:
                gp = GreenPresenting.objects.get(url=domain.url)

                # find green checks that have happened since the last listed date
                # for the given domain
                gc = Greencheck.objects.filter(
                    url=domain.url,
                    green='yes',
                    date__gt=gp.modified
                ).order_by('-date').first()

                if gc:

                    try:
                        hp = Hostingprovider.objects.get(pk=gc.hostingprovider)

                    except Hostingprovider.DoesNotExist:
                        logger.error(f"Missing hosting provider for greencheck {gc}")
                        continue

                    gp.green=GREEN
                    gp.modified=gc.date

                    gp.hosted_by_id=hp.id
                    gp.hosted_by=hp.name
                    gp.hosted_by_website=hp.website
                    partner=hp.partner


                    try:
                        gp.save()
                        updated_domains += 1
                        logger.debug(f"Added entry for {domain.url}")

                    except Exception as err:
                        logger.exception(err)
                        logger.error(f"greencheck: {gc.__dict__}, gp: {gp.__dict__}")
                        # import ipdb ; ipdb.set_trace()


            except GreenPresenting.DoesNotExist:
                gc = Greencheck.objects.filter(
                    url=domain.url, green='yes').order_by('-date').first()

                if gc:

                    try:
                        hp = Hostingprovider.objects.get(pk=gc.hostingprovider)
                    except Hostingprovider.DoesNotExist:

                        logger.error(f"Missing hosting provider for greencheck {gc}")

                        # skip this iteration
                        continue

                    except Exception as err:
                        logger.exception(err)
                        logger.error(f"greencheck: {gc.__dict__}, gp: {gp.__dict__}")


                    try:
                        gp = GreenPresenting()

                        gp.green=1
                        gp.modified=gc.date
                        gp.url=gc.url

                        gp.hosted_by_id=hp.id
                        gp.hosted_by=hp.name
                        gp.hosted_by_website=hp.website
                        gp.partner=hp.partner

                        gp.save()
                        new_domains += 1
                        logger.debug(f"Added entry for {domain.url}")
                    except Exception as err:

                        logger.exception(err)
                        logger.error(f"greencheck: {gc.__dict__}, gp: {gp.__dict__}")

                else:
                    logger.debug(f"No greencheck present for {domain.url}")

            except Exception as err:
                logger.exception(err)
                logger.error(f"greencheck: {gc.__dict__}, gp: {gp.__dict__}")
                # import ipdb ; ipdb.set_trace()

        logger.info(f"Finished updating. Total processed domains: {count}. Newly added domains: {new_domains}. Updated domains: {updated_domains}")


class Command(BaseCommand):
    help = "Update green domains list based on our list of urls in top_url table"

    def handle(self, *args, **options):
        logger.info("Adding ranges")

        top_urls = TopUrl.objects.all()
        tc_updater = TopUrlUpdater()
        tc_updater.update_green_domains(top_urls)
        logger.info("Finished")
