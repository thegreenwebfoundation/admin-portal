import logging

import dramatiq
import MySQLdb

from .models import Greencheck, GreenDomain

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@dramatiq.actor
def process_log(green_domain_args):

    green_domain = GreenDomain.from_dict(green_domain_args)

    logger.debug(f"logging a check for {green_domain.url}")

    if green_domain is not None:
        try:

            Greencheck.log_for_green_domain(green_domain)
        except MySQLdb.OperationalError as err:
            logger.warning(
                (
                    f"Problem reported by the database when trying to "
                    f"log domain: {green_domain.url}"
                )
            )
            logger.warning(err)
            return False
        except Exception as err:
            logger.exception(err)
            return False
