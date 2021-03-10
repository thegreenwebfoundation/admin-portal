# import webbrowser
import pathlib
from ..api.legacy_image_view import fetch_template_image, annotate_img
import pytest


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

