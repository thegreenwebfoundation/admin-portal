import logging

import dateutil.parser as date_parser
import datetime
import dramatiq
import MySQLdb

from one_day_to_parquet import backup_day_to_parquet

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# console = logging.StreamHandler()
# logger.addHandler(console)


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


@dramatiq.actor(queue_name="stats")
def create_stat_async(date_string: str = None, query_name: str = "total_count", *args):
    """
    Accept a date_string, and a query name then execute the query. Used to carry out
    expensive aggregation queries outside the request cycle.
    """

    from .models.stats import DailyStat

    allowed_queries = [
        "total_count",
        "total_count_for_providers",
        "top_domains_for_day",
        "top_hosting_providers_for_day",
    ]

    if query_name not in allowed_queries:
        raise Exception("Unsupported query. Ignoring")

    parsed_date = date_parser.parse(date_string)

    query_function = getattr(DailyStat, query_name)
    query_function(date_to_check=parsed_date)


@dramatiq.actor(queue_name="stats")
def backup_day_to_parquet_queue_actor(date_string: str):
    """
    Intended for use dramatiq:
    Accept a isoformat date string, convert it to a date
    and call back the day of checks to object storage as a parquert
    file.

    date_string (str): the isoformat YYYY-MM-DD string for the chosen date
    """

    try:
        target_date = datetime.date.fromisoformat(date_string)
        backup_day_to_parquet(target_date)
    except ValueError as e:
        logger.warning(
            (
                f"Could not parse a date out of the given string {date_string}. "
                "Please check that the format is YYYY-MM-DD"
            )
        )
        logger.warning(e)
