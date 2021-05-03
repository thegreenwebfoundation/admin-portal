from .templatetags import admin_helpers
import pytest

import logging

console = logging.StreamHandler()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(console)


class TestAdminHelper:
    @pytest.mark.parametrize(
        "url_to_test, expected_url",
        [
            ("www.website.in", "https://www.website.in"),
            ("http://www.website.in", "http://www.website.in"),
            ("https://www.website.in", "https://www.website.in"),
        ],
    )
    def test_make_url(self, url_to_test, expected_url):
        assert admin_helpers.make_url(url_to_test) == expected_url
