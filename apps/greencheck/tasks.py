import dramatiq

from django.utils import timezone
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


@dramatiq.actor
def create_stat_async(date_string: str = None, query_name: str = "total_count", *args):

    from .models.stats import DailyStat
    import dateutil.parser as date_parser

    allowed_queries = "total_count"

    if query_name not in allowed_queries:
        raise Exception("Unsupported query. Ignoring")

    parsed_date = date_parser.parse(date_string)

    query_function = getattr(DailyStat, query_name)
    query_function(date_to_check=parsed_date)

