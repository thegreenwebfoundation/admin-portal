import logging

from django.shortcuts import redirect

from ..models.green_domain_badge  import GreenDomainBadge, GreenDomainBadge
from ..network_utils import validate_domain

logger = logging.getLogger(__name__)


def greencheck_image(_request, url):
    """
    Show the Green Web Check badge for a given domain.
    We do this by issuing a 302 temporary redirect to the
    cached badge image in object storage - the redirect must
    be temporary in order to allow for future updates, and
    account for the fact that object storage URLS are signed (and
    therefore can expire). The GreenDomainBadge class takes care of
    checking for the presence of the image file, and creating import
    if necessary.
    """
    domain = validate_domain(url)
    badge = GreenDomainBadge.for_domain(domain)
    return redirect(badge.url)

def legacy_greencheck_image(_request, url):
    """
    We explicitly publically committed to keeping the old design
    available at the previous URL, so this has to stay for now:
    https://www.thegreenwebfoundation.org/news/rebranded-green-web-badges/
    """
    domain = validate_domain(url)
    badge = GreenDomainBadge.for_domain(domain, legacy=True)
    return redirect(badge.url)
