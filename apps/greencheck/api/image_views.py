import logging

from django.http import HttpResponse
from django.shortcuts import redirect

from ..domain_check import GreenDomainChecker
from ..models import GreenDomain
from ..badges.image_generator import GreencheckImageV3

logger = logging.getLogger(__name__)
checker = GreenDomainChecker()


def greencheck_image(request, url):
    """
    Serve the custom image request is created
    """
    green = False
    provider = None
    domain = checker.validate_domain(url)

    # `nocache=true` is the same string used by nginx. Using the same params
    # means we won't have to worry about nginx caching our request before it
    # hits an app server
    skip_cache = request.GET.get("nocache") == "true"

    checked_domain = GreenDomain.check_for_domain(domain, skip_cache)
    green = checked_domain and checked_domain.green

    if green:
        provider = checked_domain.hosted_by

    greencheck_image = GreencheckImageV3()
    img = greencheck_image.fetch_template_image(green=green)
    annotated_img = greencheck_image.annotate_img(
        img, domain, green=green, provider=provider
    )

    # responses work a bit like FileObjects, so we can write directly
    # into them, like so
    response = HttpResponse(content_type="image/png")
    annotated_img.save(response, "PNG")

    return response
