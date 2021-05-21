from typing import List
import datetime
from dateutil import rrule
import webbrowser

from django.utils import timezone

from ...accounts import models as ac_models
from .. import legacy_workers
from .. import models as gc_models


def create_greendomain(hosting_provider, sitecheck):
    green_domain = gc_models.GreenDomain(url=sitecheck.url)
    green_domain.hosted_by = hosting_provider.name
    green_domain.hosted_by_id = sitecheck.hosting_provider_id
    green_domain.hosted_by_website = hosting_provider.website
    green_domain.partner = hosting_provider.partner
    green_domain.modified = sitecheck.checked_at
    green_domain.green = sitecheck.green
    green_domain.save()

    return green_domain


def greencheck_sitecheck(
    domain,
    hosting_provider: ac_models.Hostingprovider,
    green_ip: gc_models.GreencheckIp,
):

    return gc_models.SiteCheck(
        url=domain,
        ip="192.30.252.153",
        data=True,
        green=True,
        hosting_provider_id=hosting_provider.id,
        checked_at=timezone.now(),
        match_type="ip",
        match_ip_range=green_ip.id,
        cached=True,
    )


def setup_domains(
    domains: List[str],
    hosting_provider: ac_models.Hostingprovider,
    ip_range: gc_models.GreencheckIp,
):
    """
    Set up our domains, with the corrsponding cache tables

    """
    sitecheck_logger = legacy_workers.LegacySiteCheckLogger()

    for domain in domains:
        sitecheck = greencheck_sitecheck(domain, hosting_provider, ip_range)
        sitecheck_logger.update_green_domain_caches(sitecheck, hosting_provider)

    # assert gc_models.GreenDomain.objects.all().count() == len(domains)


def range_of_dates(
    start_datetime: datetime.datetime = None, end_datetime: datetime.datetime = None
) -> List[datetime.date]:
    """
    Return the a range dates, given a start and end datetime
    """
    # gemerate dates for last month
    date_range = rrule.rrule(
        freq=rrule.DAILY, dtstart=start_datetime.date(), until=end_datetime.date()
    )
    return [date for date in date_range]


def view_in_browser(content):
    """
    Accepts a bytestring and render it
    with the system browser
    """
    with open("webpage.html", "w") as page:
        page.write(content.decode("utf-8"))

    webbrowser.open("webpage.html")
