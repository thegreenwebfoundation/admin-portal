from .templatetags import admin_helpers
import pytest

import logging

console = logging.StreamHandler()
logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
# logger.addHandler(console)


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

    def test_link_to_ripe_stat_returns_ip(self, mocker):
        # we don't want to do an network call every time we run this test
        # if we don't mock `convert_domain_to_ip`, then end up doing a
        # dns lookup each time we run this test.
        mock_method = mocker.patch(
            "apps.theme.templatetags.admin_helpers.convert_domain_to_ip",
            return_value="8.8.8.8",
        )
        assert "8.8.8.8" in admin_helpers.link_to_ripe_stat("https://google.com")
        # sanity check to see we're actually using the mock_method in the test
        assert mock_method.call_count == 1

    def test_link_to_ripe_stat_handles_empty(self, mocker):
        result = admin_helpers.link_to_ripe_stat(None)
        assert result == ""

    def test_link_to_ripe_stat_handles_failing_lookup(self, mocker):
        # Added to cover the case when there is a valid domain, but it doesn't
        # resolve to an IP address. For more see the links below
        # https://product-science.sentry.io/issues/5253649009/
        # https://github.com/thegreenwebfoundation/admin-portal/pull/575

        result = admin_helpers.link_to_ripe_stat("valid-but-not-resolving-to-ip.com")
        assert result == ""
