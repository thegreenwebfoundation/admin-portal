# from typing import Boolean
from pathlib import Path
import logging

from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.cache import cache_page
from PIL import Image, ImageDraw, ImageFont
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import AllowAny
from rest_framework_jsonp.renderers import JSONPRenderer

from ..domain_check import GreenDomainChecker
from ..models import GreenDomain

TEXT_COLOR = (0, 0, 0)
TEXT_POSITION_LEFT = 15

app_dir = Path(__file__).parent.parent
font_path = app_dir / "badges" / "TWKEverett-Regular.otf"

font_settings_green = ImageFont.truetype(str(font_path), 10)
font_settings_grey = ImageFont.truetype(str(font_path), 9)

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


def fetch_template_image(domain, green=False) -> Image:
    """
    Fetch our image, return the image object, that we can
    then annotate to make our badge.
    """
    if green:
        color = "green"
    else:
        color = "grey"

    app_dir = Path(__file__).parent.parent
    img_path = app_dir / "badges" / f"blank-badge-{color}.png"
    img = Image.open(img_path)
    return img


def add_hosted_text(draw, text_color, domain, provider=None, green=False):

    if green:
        if provider:
            draw.text((TEXT_POSITION_LEFT, 43), f"{domain}", TEXT_COLOR, font=font_settings_green)
            hosted_by_message = f"hosted by {provider}"
            draw.text((TEXT_POSITION_LEFT, 55), hosted_by_message, text_color, font=font_settings_green)
        else:
            draw.text((TEXT_POSITION_LEFT, 50), f"{domain}", TEXT_COLOR, font=font_settings_green)
    else:
        draw.text((TEXT_POSITION_LEFT, 53), f"{domain}", TEXT_COLOR, font=font_settings_grey)



def annotate_img(img, domain, green=False, provider=None) -> Image:
    """
    Annotate image with the required information
    """
    draw = ImageDraw.Draw(img)

    if green:
        
        add_hosted_text(
            draw,
            TEXT_COLOR,
            domain,
            provider=provider,
            green=True,
        )
        return img
    else:
        add_hosted_text(
            draw,
            TEXT_COLOR,
            domain,
            provider=provider,
            green=False,
        )
        return img


# @cache_page(60 * 15)
def legacy_greencheck_image(request, url):
    """
    Serve the custom image request is created
    """
    # if the request type is text, we assume a user is following the
    # url in a browser. we redirect to the greencheck page
    green = False
    provider = None

    # browser_visit = check_for_browser_visit(request)
    browser_visit = False

    domain = checker.validate_domain(url)

    if browser_visit:
        return redirect(
            f"https://www.thegreenwebfoundation.org/green-web-check/?url={domain}"
        )

    # `nocache=true` is the same string used by nginx. Using the same params
    # means we won't have to worry about nginx caching our request before it
    # hits an app server
    skip_cache = request.GET.get("nocache") == "true"

    checked_domain = GreenDomain.check_for_domain(domain, skip_cache)
    green = checked_domain and checked_domain.green

    if green:
        provider = checked_domain.hosted_by

    img = fetch_template_image(url, green=green)
    annotated_img = annotate_img(img, domain, green=green, provider=provider)

    # responses work a bit like FileObjects, so we can write directly into like so
    response = HttpResponse(content_type="image/png")
    annotated_img.save(response, "PNG")

    return response
