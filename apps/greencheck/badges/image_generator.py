import logging

from pathlib import Path


from PIL import Image, ImageDraw, ImageFont


from apps.accounts.models import Hostingprovider

app_dir = Path(__file__).parent.parent  #

logger = logging.getLogger(__name__)


class GreencheckImageV2:
    """
    The image generator used for creating the greencheck badges
    before 2024. Uses the earlier branding from before 2022.
    """

    GREEN_DOMAIN_TEXT_COLOR = (00, 70, 00)
    GREEN_DOMAIN_TEXT_SHADOW = (79, 138, 74)
    GREEN_HOSTED_BY_TEXT_COLOR = (255, 255, 255)
    GREEN_HOSTED_BY_SHADOW_COLOR = (93, 173, 19)

    GREY_DOMAIN_TEXT_COLOR = (100, 100, 100)
    GREY_DOMAIN_TEXT_SHADOW = (170, 170, 170)
    GREY_HOSTED_BY_TEXT_COLOR = (255, 255, 255)
    GREY_HOSTED_BY_TEXT_SHADOW = (210, 210, 210)

    font_path = app_dir / "badges" / "OpenSans-Regular.ttf"
    domain_font = ImageFont.truetype(str(font_path), 14)
    hosted_by_font = ImageFont.truetype(str(font_path), 11)

    def fetch_template_image(self, green: bool = False) -> Image:
        """
        Fetch our image, return the image object, that we can
        then annotate to make our badge.
        """
        if green:
            color = "green"
        else:
            color = "grey"

        app_dir = Path(__file__).parent.parent
        img_path = app_dir / "badges" / f"blank-badge-{color}-v2.png"
        img = Image.open(img_path)
        return img

    def add_domain_text(
        self, draw: ImageDraw, domain: str, text_color: tuple, text_shadow: tuple
    ):
        """
        Add the name of the domain being checked to the image at the
        given coordinates
        """
        left_inside_block = (18, 80)
        left_inside_block_offset = (17, 79)

        draw.text(
            left_inside_block_offset, f"{domain}", text_shadow, font=self.domain_font
        )
        draw.text(left_inside_block, f"{domain}", text_color, font=self.domain_font)

    def add_hosted_text(
        self,
        draw: ImageDraw,
        text_color: tuple,
        text_shadow: tuple,
        provider: Hostingprovider = None,
        green=False,
    ):
        """
        Add the secondary text explaining what the result means
        """
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
            left_inside_block_offset,
            hosted_by_message,
            text_shadow,
            font=self.hosted_by_font,
        )
        draw.text(
            left_inside_block, hosted_by_message, text_color, font=self.hosted_by_font
        )

    def annotate_img(
        self,
        img: Image,
        domain: str,
        green: bool = False,
        provider: Hostingprovider = None,
    ) -> Image:
        """
        Annotate image with the required information
        """
        draw = ImageDraw.Draw(img)

        if green:
            self.add_domain_text(
                draw,
                domain,
                self.GREEN_DOMAIN_TEXT_COLOR,
                self.GREEN_DOMAIN_TEXT_SHADOW,
            )
            self.add_hosted_text(
                draw,
                self.GREEN_HOSTED_BY_TEXT_COLOR,
                self.GREEN_HOSTED_BY_SHADOW_COLOR,
                provider=provider,
                green=True,
            )
            return img
        else:
            self.add_domain_text(
                draw,
                domain,
                self.GREY_DOMAIN_TEXT_COLOR,
                self.GREY_DOMAIN_TEXT_SHADOW,
            )
            self.add_hosted_text(
                draw,
                self.GREY_HOSTED_BY_TEXT_COLOR,
                self.GREY_HOSTED_BY_TEXT_SHADOW,
                provider=provider,
                green=False,
            )
            return img


class GreencheckImageV3:
    """
    The image generator used for creating the png greencheck badges from
    March 2024 onwards.
    """

    TEXT_COLOR = (0, 0, 0)
    TEXT_POSITION_LEFT = 12

    font_path = app_dir / "badges" / "TWKEverett-Regular.otf"
    font_settings_green = ImageFont.truetype(str(font_path), 9)
    font_settings_grey = ImageFont.truetype(str(font_path), 9)

    @classmethod
    def generate_greencheck_image(cls, domain, green, hosting_provider_name):
        generator = cls()
        img = generator.fetch_template_image(green=green)
        annotated_img = generator.annotate_img(
            img, domain, green=green, provider=hosting_provider_name
        ).convert("RGB")
        return annotated_img

    def normalise_domain_name_length(self, domain: str) -> str:
        """
        Truncate the domain name if it's too long,
        to fit in the badge
        """
        if len(domain) > 30:
            shortened_name = domain[:30]
            # add the ellipsis to show it's been shortened
            return f"{shortened_name}..."

        return domain

    def fetch_template_image(self, green: bool = False) -> Image:
        """
        Fetch our image, return the image object, that we can
        then annotate to make our badge.
        """
        if green:
            color = "green"
        else:
            color = "grey"

        img_path = app_dir / "badges" / f"blank-badge-{color}-v3.png"
        img = Image.open(img_path)
        return img

    def add_hosted_text(self, draw, text_color, domain, provider=None, green=False):

        # is the name too long ? shorten if so
        domain = self.normalise_domain_name_length(domain)

        if green:
            if provider:
                draw.text(
                    (self.TEXT_POSITION_LEFT, 43),
                    f"{domain}",
                    self.TEXT_COLOR,
                    font=self.font_settings_green,
                )
                hosted_by_message = f"Hosted by {provider}"
                draw.text(
                    (self.TEXT_POSITION_LEFT, 55),
                    hosted_by_message,
                    text_color,
                    font=self.font_settings_green,
                )
            else:
                draw.text(
                    (self.TEXT_POSITION_LEFT, 40),
                    f"{domain}",
                    self.TEXT_COLOR,
                    font=self.font_settings_green,
                )
        else:
            no_evidence_message = "No evidence found for green hosting"
            draw.text(
                (self.TEXT_POSITION_LEFT, 43),
                no_evidence_message,
                self.TEXT_COLOR,
                font=self.font_settings_green,
            )
            draw.text(
                (self.TEXT_POSITION_LEFT, 55),
                f"{domain}",
                self.TEXT_COLOR,
                font=self.font_settings_grey,
            )

    def annotate_img(
        self,
        img: Image,
        domain: str,
        green: bool = False,
        provider: Hostingprovider = None,
    ) -> Image:
        """
        Annotate image with the required information
        """
        draw = ImageDraw.Draw(img)

        if green:

            self.add_hosted_text(
                draw,
                self.TEXT_COLOR,
                domain,
                provider=provider,
                green=True,
            )
            return img
        else:
            self.add_hosted_text(
                draw,
                self.TEXT_COLOR,
                domain,
                provider=provider,
                green=False,
            )
            return img
