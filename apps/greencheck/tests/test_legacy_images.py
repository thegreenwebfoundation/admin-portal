# import webbrowser
import pathlib
from django.urls import reverse
import pytest
import webbrowser

from ..api.legacy_image_view import annotate_img, fetch_template_image
from ..models import GreencheckIp, Hostingprovider
from . import setup_domains


class TestGreenBadgeGenerator:
    @pytest.mark.parametrize("green", [True, False])
    def test_fetch_template_image(self, tmpdir, green):
        """
        """
        test_filename = f"test_greencheck_image_{green}.png"
        domain = "google.com"

        img = fetch_template_image(domain, green=green)
        img_path = str(pathlib.Path(tmpdir) / test_filename)
        img.save(img_path)
        # is it an image file?
        assert img.format == "PNG"
        # webbrowser.open(img_path)

    def test_annotate_image_green(self, tmpdir):
        test_filename = f"test_greencheck_image_green.png"
        domain = "google.com"

        if pathlib.Path(test_filename).exists():
            pathlib.Path(test_filename).unlink()

        img = fetch_template_image(domain, green=True)
        updated_img = annotate_img(img, domain, green=True)
        img_path = str(pathlib.Path(tmpdir) / test_filename)
        updated_img.save(img_path)
        # webbrowser.open(img_path)

    def test_annotate_image_green_with_provider(self, tmpdir):
        test_filename = f"test_greencheck_image_green.png"
        domain = "google.com"

        if pathlib.Path(test_filename).exists():
            pathlib.Path(test_filename).unlink()

        img = fetch_template_image(domain, green=True)
        updated_img = annotate_img(img, domain, green=True, provider="Google Inc")
        img_path = str(pathlib.Path(tmpdir) / test_filename)
        updated_img.save(img_path)
        assert img.format == "PNG"
        # webbrowser.open(img_path)

    # @pytest.mark.skip()
    def test_annotate_image_grey(self, tmpdir):
        test_filename = f"test_greencheck_image_grey.png"
        domain = "google.com"

        if pathlib.Path(test_filename).exists():
            pathlib.Path(test_filename).unlink()

        img = fetch_template_image(domain, green=False)
        updated_img = annotate_img(img, domain)
        img_path = str(pathlib.Path(tmpdir) / test_filename)
        updated_img.save(img_path)
        assert img.format == "PNG"
        # webbrowser.open(img_path)


class TestGreencheckImageView:
    def test_download_greencheck_image_green(
        self,
        db,
        hosting_provider_with_sample_user: Hostingprovider,
        green_ip: GreencheckIp,
        client,
    ):
        """
        Hit the greencheckimage endpoint to download a badge image for a green provider
        """
        website = "some_green_site.com"

        setup_domains([website], hosting_provider_with_sample_user, green_ip)

        url_path = reverse("legacy-greencheck-image", args=[website])

        response = client.get(url_path)

        with open(f"{website}.png", "wb") as imgfile:
            imgfile.write(response.content)

        webbrowser.open(f"{website}.png")

        assert response.status_code == 200

    def test_download_greencheck_image_grey(
        self, db, client,
    ):
        """
        Hit the greencheckimage endpoint to download a badge image for a green provider
        """
        website = "some_grey_site.com"

        url_path = reverse("legacy-greencheck-image", args=[website])

        response = client.get(url_path)

        with open(f"{website}.png", "wb") as imgfile:
            imgfile.write(response.content)

        webbrowser.open(f"{website}.png")

        assert response.status_code == 200

    def test_redirected_when_browsing_to_greencheck_image(
        self, db, client,
    ):
        """
        When a user tries to visit the badge, we redirect them to the main site
        """
        website = "some_grey_site.com"

        url_path = reverse("legacy-greencheck-image", args=[website])

        # We simulate a browser and sending accept headers with HTTP_ACCEPT="*/*"
        response = client.get(url_path, HTTP_ACCEPT="*/*")

        assert response.status_code == 302

