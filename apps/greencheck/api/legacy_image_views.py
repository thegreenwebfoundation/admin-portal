import logging

from django.http import HttpResponse
from django.shortcuts import redirect


from ..domain_check import GreenDomainChecker
from ..models import GreenDomain
from ..badges.image_generator import GreencheckImageV2


logger = logging.getLogger(__name__)
checker = GreenDomainChecker()


def check_for_browser_visit(request) -> bool:
    """
    Check if the request is a browser visiting this
    as the main url, rather than requesting an image.
    """

    accepted_headers = request.headers.get("Accept")
    logger.info(f"accepted_headers - {accepted_headers}")
    if accepted_headers:
        return "text/html" in accepted_headers or "*/*" in accepted_headers


def legacy_greencheck_image(request, url):
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

    greencheck_image = GreencheckImageV2()
    img = greencheck_image.fetch_template_image(green=green)
    annotated_img = greencheck_image.annotate_img(
        img, domain, green=green, provider=provider
    )

    # responses work a bit like FileObjects, so we can write directly
    # into them, like so
    response = HttpResponse(content_type="image/png")
    annotated_img.save(response, "PNG")

    return response
