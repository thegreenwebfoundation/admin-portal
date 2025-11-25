import logging

from pathlib import Path


from PIL import Image, ImageDraw, ImageFont


from apps.accounts.models import Hostingprovider

app_dir = Path(__file__).parent.parent  #

logger = logging.getLogger(__name__)

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
    def generate_greencheck_image(cls, domain : str, green : bool, hosting_provider_name : str) -> Image:
        """
        Generates and returns the green web badge image for a given domain.
        """
        generator = cls()
        img = generator.fetch_template_image(green=green)
        annotated_img = generator.annotate_img(
            img, domain, green=green, provider=hosting_provider_name
        ).convert("RGBA")
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
