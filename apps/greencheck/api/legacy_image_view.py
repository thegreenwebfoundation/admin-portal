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

GREEN_DOMAIN_TEXT_COLOR = (00, 70, 00)
GREEN_DOMAIN_TEXT_SHADOW = (79, 138, 74)
GREEN_HOSTED_BY_TEXT_COLOR = (255, 255, 255)
GREEN_HOSTED_BY_SHADOW_COLOR = (93, 173, 19)

GREY_DOMAIN_TEXT_COLOR = (100, 100, 100)
GREY_DOMAIN_TEXT_SHADOW = (170, 170, 170)
GREY_HOSTED_BY_TEXT_COLOR = (255, 255, 255)
GREY_HOSTED_BY_TEXT_SHADOW = (210, 210, 210)

app_dir = Path(__file__).parent.parent
font_path = app_dir / "badges" / "OpenSans-Regular.ttf"
domain_font = ImageFont.truetype(str(font_path), 14)
hosted_by_font = ImageFont.truetype(str(font_path), 11)

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


def add_domain_text(draw, domain, text_color, text_shadow):
    left_inside_block = (18, 80)
    left_inside_block_offset = (17, 79)

    draw.text(left_inside_block_offset, f"{domain}", text_shadow, font=domain_font)
    draw.text(left_inside_block, f"{domain}", text_color, font=domain_font)


def add_hosted_text(draw, text_color, text_shadow, provider=None, green=False):

    left_inside_block = (18, 100)
    left_inside_block_offset = (18, 100)

    if green:
        if provider:
            hosted_by_message = f"is green hosted by {provider}."
        else:
            hosted_by_message = "is hosted green."
    else:
        hosted_by_message = "is hosted grey"

    draw.text(
        left_inside_block_offset, hosted_by_message, text_shadow, font=hosted_by_font
    )
    draw.text(left_inside_block, hosted_by_message, text_color, font=hosted_by_font)


def annotate_img(img, domain, green=False, provider=None) -> Image:
    """
    Annotate image with the required information
    """
    draw = ImageDraw.Draw(img)

    if green:
        add_domain_text(draw, domain, GREEN_DOMAIN_TEXT_COLOR, GREEN_DOMAIN_TEXT_SHADOW)
        add_hosted_text(
            draw,
            GREEN_HOSTED_BY_TEXT_COLOR,
            GREEN_HOSTED_BY_SHADOW_COLOR,
            provider=provider,
            green=True,
        )
        return img
    else:
        add_domain_text(draw, domain, GREY_DOMAIN_TEXT_COLOR, GREY_DOMAIN_TEXT_SHADOW)
        add_hosted_text(
            draw,
            GREY_HOSTED_BY_TEXT_COLOR,
            GREY_HOSTED_BY_TEXT_SHADOW,
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
    green_domain = None
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

    if request.GET.get("nocache") == "true":
        sitecheck = checker.perform_full_lookup(domain)
        if sitecheck.green:
            green_domain = GreenDomain.from_sitecheck(sitecheck)
    else:
        green_domain = GreenDomain.objects.filter(url=domain).first()

    if green_domain:
        green = True
        provider = green_domain.hosted_by

    img = fetch_template_image(url, green=green)
    annotated_img = annotate_img(img, domain, green=green, provider=provider)

    # responses work a bit like FileObjects, so we can write directly into like so
    response = HttpResponse(content_type="image/png")
    annotated_img.save(response, "PNG")

    return response
