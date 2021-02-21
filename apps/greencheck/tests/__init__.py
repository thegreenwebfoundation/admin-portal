from django.utils import timezone

from apps.greencheck.models import GreencheckIp, Hostingprovider, GreenDomain
from apps.greencheck.legacy_workers import SiteCheck


def create_greendomain(hosting_provider, sitecheck):
    green_domain = GreenDomain(url=sitecheck.url)
    green_domain.hosted_by = hosting_provider.name
    green_domain.hosted_by_id = sitecheck.hosting_provider_id
    green_domain.hosted_by_website = hosting_provider.website
    green_domain.partner = hosting_provider.partner
    green_domain.modified = sitecheck.checked_at
    green_domain.green = sitecheck.green
    green_domain.save()

    return green_domain


def greencheck_sitecheck(
    domain, hosting_provider: Hostingprovider, green_ip: GreencheckIp
):

    return SiteCheck(
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
