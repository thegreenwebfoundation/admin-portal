# from typing import Boolean
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
from pathlib import Path

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


def parse_domain_from_url(url):
    """"""
    pass


def check_for_browser_visit(request) -> bool:
    """
    Check if the request is a browser visiting this
    as the main url. Instead of showing the image,
    we redirect to the page.
    """
    pass


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
    img_path = app_dir / "badges" / f"150119{color}.png"
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


def legacy_greencheck_image(request, url):
    """
    Serve the custom image request is created
    """
    # if the request type is text, we assume a user is following the
    # url in a browser. we redirect to the greencheck page
    browser_visit = check_for_browser_visit(request)

    if browser_visit:
        # redirect_to_main_site(())
        pass

    domain = parse_domain_from_url(url)
    img = fetch_template_image(green=True)
    annotated_img = add_details(domain)

    return annotated_img
