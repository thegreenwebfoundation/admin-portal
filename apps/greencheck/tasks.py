import logging

import dramatiq
import MySQLdb

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@dramatiq.actor
def process_log(sitecheck_args):
    from .models import Greencheck, SiteCheck # Prevent circular import error
    sitecheck = SiteCheck(**sitecheck_args)

    logger.debug(f"logging a check for {sitecheck.url}")

    if sitecheck is not None:
        try:

            Greencheck.log_for_sitecheck(sitecheck)
        except MySQLdb.OperationalError as err:
            logger.warning(
                (
                    f"Problem reported by the database when trying to "
                    f"log domain: {sitecheck.url}"
                )
            )
            logger.warning(err)
            return False
        except Exception as err:
            logger.exception(err)
            return False
