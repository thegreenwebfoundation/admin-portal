import logging

from django.shortcuts import redirect
from django.core.files.storage import default_storage

from ..domain_check import GreenDomainChecker
from ..models import GreenDomain
from ..badges.image_generator import GreencheckImageV3

logger = logging.getLogger(__name__)
checker = GreenDomainChecker()


def greencheck_image(request, url):
    """
    Serve the custom image request is created
    """
    domain = checker.validate_domain(url)
    greencheck_image = GreencheckImageV3()
    image_name = greencheck_image.image_path_for(domain)
    if not default_storage.exists(image_name):
        checked_domain = GreenDomain.check_for_domain(domain)
        greencheck_image.generate_greencheck_image(domain, checked_domain)
    return redirect(default_storage.url(image_name))

