import dramatiq

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console = logging.StreamHandler()
logger.addHandler(console)


@dramatiq.actor
def process_log(domain):
    from .workers import SiteCheckLogger

    check_logger = SiteCheckLogger()

    logger.debug(f"logging a check for {domain}")
    check_logger.log_sitecheck_for_domain(domain)
