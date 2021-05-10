from django.utils import dateparse, timezone
from apps.greencheck.models import Greencheck, GreenDomain, SiteCheck
from apps.accounts.models import Hostingprovider
import django


import socket
import datetime
import tld
import ipaddress
import logging

console = logging.StreamHandler()
logger = logging.getLogger(__name__)
# logger.setLevel(logging.WARN)
# logger.addHandler(console)


class SiteCheckLogger:
    """
    A worker to consume messages from RabbitMQ, generated by the
    dramatiq library in this application
    """

    def log_sitecheck_for_domain(self, url: str):
        """
        Asynchronously log a sitecheck
        """
        from .domain_check import GreenDomainChecker

        checker = GreenDomainChecker()

        try:
            sitecheck = checker.check_domain(url)
        # we don't have a recognisable domain name that we can resolve
        except UnicodeError:
            # exit early, we do nothing further
            logger.info(
                (
                    f"{url} doesn't appear to be a domain we can look up. "
                    "Not logging a check."
                )
            )
            return None
        # we have resolved the domain, but it's not a valid IP address
        # that we can look up (i.e. a private, internal IP, or localhost)
        except socket.gaierror:
            # exit early, we do nothing further
            logger.info(
                (
                    f"{url} doesn't appear to be a domain we can look up. "
                    "Not logging a check."
                )
            )
            return None

        if sitecheck.checked_at:
            sitecheck.checked_at = str(sitecheck.checked_at)
        else:
            sitecheck.checked_at = str(timezone.now())
        self.log_sitecheck_to_database(sitecheck)

    def log_sitecheck_to_database(self, sitecheck: SiteCheck):
        """
        Accept a sitecheck and log to the greencheck logging table,
        along with the green domains table (green_presenting).

        """
        logger.debug(sitecheck)

        try:
            hosting_provider = Hostingprovider.objects.get(
                pk=sitecheck.hosting_provider_id
            )
        except Hostingprovider.DoesNotExist:
            # if we have no hosting provider we leave it out
            hosting_provider = None

        if sitecheck.green and hosting_provider:
            self.update_green_domain_caches(sitecheck, hosting_provider)

        try:
            fixed_tld, *_ = (tld.get_tld(sitecheck.url, fix_protocol=True),)
        except tld.exceptions.TldDomainNotFound:

            if sitecheck.url == "localhost":
                return {
                    "status": "We can't look up localhost. Skipping.",
                    "sitecheck": sitecheck,
                }

            try:
                ipaddress.ip_address(sitecheck.url)
                fixed_tld = ""
            except Exception:
                logger.warning(
                    (
                        "not a domain, or an IP address, not logging. "
                        f"Sitecheck results: {sitecheck}"
                    )
                )
                return {"status": "Error", "sitecheck": sitecheck}

        except Exception:
            logger.exception(
                (
                    "Unexpected error. Not logging the result. "
                    f"Sitecheck results: {sitecheck}"
                )
            )
            return {"status": "Error", "sitecheck": sitecheck}

        # finally write to the greencheck table
        if isinstance(sitecheck.checked_at, datetime.datetime):
            sitecheck.checked_at = str(sitecheck.checked_at)

        if hosting_provider:
            res = Greencheck.objects.create(
                hostingprovider=hosting_provider.id,
                greencheck_ip=sitecheck.match_ip_range,
                date=dateparse.parse_datetime(sitecheck.checked_at),
                green="yes",
                ip=sitecheck.ip,
                tld=fixed_tld,
                type=sitecheck.match_type,
                url=sitecheck.url,
            )
            logger.debug(f"Greencheck logged: {res}")
        else:

            res = Greencheck.objects.create(
                date=dateparse.parse_datetime(sitecheck.checked_at),
                green="no",
                ip=sitecheck.ip,
                tld=fixed_tld,
                url=sitecheck.url,
            )
            logger.debug(f"Greencheck logged: {res}")

        # return result so we can inspect if need be
        return {"status": "OK", "sitecheck": sitecheck, "res": res}

    def update_green_domain_caches(
        self, sitecheck: SiteCheck, hosting_provider: Hostingprovider
    ):
        """
        Update the caches - namely the green domains table, and if running Redis
        """

        try:
            green_domain = GreenDomain.objects.get(url=sitecheck.url)
        except GreenDomain.DoesNotExist:
            green_domain = GreenDomain(url=sitecheck.url)

        green_domain.hosted_by = hosting_provider.name
        green_domain.hosted_by_id = sitecheck.hosting_provider_id
        green_domain.hosted_by_website = hosting_provider.website
        green_domain.partner = hosting_provider.partner
        green_domain.modified = sitecheck.checked_at
        green_domain.green = sitecheck.green
        try:
            green_domain.save()
            self.update_redis_domain_cache(green_domain)
        except django.db.utils.IntegrityError:
            logger.info(f"skipping update to the cache table for {sitecheck.url}")

    def update_redis_domain_cache(self, green_domain: GreenDomain):
        """
        Accept a GreenDomain object, and write it to the corresponding
        redis cache keys
        """
        # TODO: this is primarily used for logger processes
        # write it to the domains namespace

        # write it to the recent domains collection

        pass
