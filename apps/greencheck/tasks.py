import dramatiq

import logging

import MySQLdb

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console = logging.StreamHandler()
logger.addHandler(console)


@dramatiq.actor
def process_log(domain):
    from .workers import SiteCheckLogger

    check_logger = SiteCheckLogger()

    logger.debug(f"logging a check for {domain}")
    if domain is not None:
        try:
            check_logger.log_sitecheck_for_domain(domain)
        except MySQLdb.OperationalError as err:
            logger.warning(
                (
                    f"Problem reported by the database when trying to "
                    f"log domain: {domain}"
                )
            )
            logger.warning(err)
            return False
        except Exception as err:
            logger.exception(err)
            return False

