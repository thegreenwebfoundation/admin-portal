import pathlib
import webbrowser

import pytest
from django.urls import reverse

from apps.greencheck.badges.image_generator import GreencheckImageV2, GreencheckImageV3
from ..models import GreencheckIp
from ...accounts import models as ac_models
from . import setup_domains


class TestGreenBadgeGeneratorV2:
    @pytest.mark.parametrize("green", [True, False])
    def test_fetch_template_image(self, tmpdir, green):
        """ """
        test_filename = "test_greencheck_image_{green}.png"

        image_generator = GreencheckImageV2()

        img = image_generator.fetch_template_image(green=green)
        img_path = str(pathlib.Path(tmpdir) / test_filename)
        img.save(img_path)
        # is it an image file?
        assert img.format == "PNG"
        # webbrowser.open(img_path)

    def test_annotate_image_green(self, tmpdir):
        test_filename = "test_greencheck_image_green.png"
        domain = "google.com"

        if pathlib.Path(test_filename).exists():
            pathlib.Path(test_filename).unlink()

        image_generator = GreencheckImageV2()
        img = image_generator.fetch_template_image(green=True)
        updated_img = image_generator.annotate_img(img, domain, green=True)

        img_path = str(pathlib.Path(tmpdir) / test_filename)
        updated_img.save(img_path)
        # webbrowser.open(img_path)

    def test_annotate_image_green_with_provider(self, tmpdir):
        test_filename = "test_greencheck_image_green.png"
        domain = "google.com"

        if pathlib.Path(test_filename).exists():
            pathlib.Path(test_filename).unlink()

        image_generator = GreencheckImageV2()
        img = image_generator.fetch_template_image(green=True)
        updated_img = image_generator.annotate_img(
            img, domain, green=True, provider="Google Inc"
        )
        img_path = str(pathlib.Path(tmpdir) / test_filename)
        updated_img.save(img_path)
        assert img.format == "PNG"
        # webbrowser.open(img_path)

    # @pytest.mark.skip()
    def test_annotate_image_grey(self, tmpdir):
        test_filename = "test_greencheck_image_grey.png"
        domain = "google.com"

        if pathlib.Path(test_filename).exists():
            pathlib.Path(test_filename).unlink()

        image_generator = GreencheckImageV2()
        img = image_generator.fetch_template_image(green=False)
        updated_img = image_generator.annotate_img(img, domain)
        img_path = str(pathlib.Path(tmpdir) / test_filename)
        updated_img.save(img_path)
        assert img.format == "PNG"
        # webbrowser.open(img_path)


class TestGreenBadgeGeneratorV3:
    @pytest.mark.parametrize("green", [True, False])
    def test_fetch_template_image(self, tmpdir, green):
        """ """
        test_filename = "test_greencheck_image_{green}.png"

        image_generator = GreencheckImageV3()

        img = image_generator.fetch_template_image(green=green)
        img_path = str(pathlib.Path(tmpdir) / test_filename)
        img.save(img_path)
        # is it an image file?
        assert img.format == "PNG"
        # webbrowser.open(img_path)

    def test_annotate_image_green(self, tmpdir):
        test_filename = "test_greencheck_image_green.png"
        domain = "google.com"

        if pathlib.Path(test_filename).exists():
            pathlib.Path(test_filename).unlink()

        image_generator = GreencheckImageV3()
        img = image_generator.fetch_template_image(green=True)
        updated_img = image_generator.annotate_img(img, domain, green=True)

        img_path = str(pathlib.Path(tmpdir) / test_filename)
        updated_img.save(img_path)
        # webbrowser.open(img_path)

    def test_annotate_image_green_with_provider(self, tmpdir):
        test_filename = "test_greencheck_image_green.png"
        domain = "google.com"

        if pathlib.Path(test_filename).exists():
            pathlib.Path(test_filename).unlink()

        image_generator = GreencheckImageV3()
        img = image_generator.fetch_template_image(green=True)
        updated_img = image_generator.annotate_img(
            img, domain, green=True, provider="Google Inc"
        )
        img_path = str(pathlib.Path(tmpdir) / test_filename)
        updated_img.save(img_path)
        assert img.format == "PNG"
        # webbrowser.open(img_path)

    # @pytest.mark.skip()
    def test_annotate_image_grey(self, tmpdir):
        test_filename = "test_greencheck_image_grey.png"
        domain = "google.com"

        if pathlib.Path(test_filename).exists():
            pathlib.Path(test_filename).unlink()

        image_generator = GreencheckImageV3()
        img = image_generator.fetch_template_image(green=False)
        updated_img = image_generator.annotate_img(img, domain)
        img_path = str(pathlib.Path(tmpdir) / test_filename)
        updated_img.save(img_path)
        assert img.format == "PNG"
        # webbrowser.open(img_path)


class TestGreencheckImageViewV2:
    def test_download_greencheck_image_green(
        self,
        db,
        hosting_provider_with_sample_user: ac_models.Hostingprovider,
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

        # webbrowser.open(f"{website}.png")

        assert response.status_code == 200

    def test_download_greencheck_image_grey(
        self,
        db,
        client,
    ):
        """
        Hit the greencheckimage endpoint to download a badge image for a green provider
        """
        website = "some_grey_site.com"

        url_path = reverse("greencheck-image", args=[website])

        response = client.get(url_path)

        with open(f"{website}.png", "wb") as imgfile:
            imgfile.write(response.content)

        # webbrowser.open(f"{website}.png")

        assert response.status_code == 200

    def test_download_greencheck_image_green_nocache(
        self,
        db,
        client,
        hosting_provider_with_sample_user: ac_models.Hostingprovider,
        green_ip: GreencheckIp,
    ):
        """
        Check we have support for 'nocache' - this gives us a slow check
        in return for always returning the results from a network, rather than
        checking any locally cached result in nginx, redis, or the database.
        """

        website = green_ip.ip_start
        url_path = reverse("greencheck-image", args=[website])

        response = client.get(url_path, {"nocache": "true"})

        with open(f"{website}.png", "wb") as imgfile:
            imgfile.write(response.content)

        # webbrowser.open(f"{website}.png")

        assert response.status_code == 200


class TestGreencheckImageViewV3:
    def test_download_greencheck_image_green(
        self,
        db,
        hosting_provider_with_sample_user: ac_models.Hostingprovider,
        green_ip: GreencheckIp,
        client,
    ):
        """
        Hit the greencheckimage endpoint to download a badge image for a green provider
        """
        website = "some_green_site.com"

        setup_domains([website], hosting_provider_with_sample_user, green_ip)

        url_path = reverse("greencheck-image", args=[website])

        response = client.get(url_path)

        with open(f"{website}.png", "wb") as imgfile:
            imgfile.write(response.content)

        # webbrowser.open(f"{website}.png")

        assert response.status_code == 200

    def test_download_greencheck_image_grey(
        self,
        db,
        client,
    ):
        """
        Hit the greencheckimage endpoint to download a badge image for a green provider
        """
        website = "some_grey_site.com"

        url_path = reverse("greencheck-image", args=[website])

        response = client.get(url_path)

        with open(f"{website}.png", "wb") as imgfile:
            imgfile.write(response.content)

        # webbrowser.open(f"{website}.png")

        assert response.status_code == 200

    def test_download_greencheck_image_green_nocache(
        self,
        db,
        client,
        hosting_provider_with_sample_user: ac_models.Hostingprovider,
        green_ip: GreencheckIp,
    ):
        """
        Check we have support for 'nocache' - this gives us a slow check
        in return for always returning the results from a network, rather than
        checking any locally cached result in nginx, redis, or the database.
        """

        website = green_ip.ip_start
        url_path = reverse("greencheck-image", args=[website])

        response = client.get(url_path, {"nocache": "true"})

        with open(f"{website}.png", "wb") as imgfile:
            imgfile.write(response.content)

        # webbrowser.open(f"{website}.png")

        assert response.status_code == 200
