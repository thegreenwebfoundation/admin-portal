import logging

from django.shortcuts import redirect

from ..domain_check import GreenDomainChecker
from ..models.images  import GreenDomainBadge

logger = logging.getLogger(__name__)
checker = GreenDomainChecker()


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
    domain = checker.validate_domain(url)
    badge = GreenDomainBadge.for_domain(domain)
    return redirect(badge.url)

