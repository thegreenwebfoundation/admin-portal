import pytest
import ipaddress
import json
from django.urls import reverse

import logging
logger = logging.getLogger(__name__)


@pytest.mark.django_db
class TestTryout:

    @pytest.mark.only
    def test_tryout_performs_lookup(self, client, hosting_user):
        """
        Check that we use the provided library lookup the IP address
        for the provided url, and use ipwhois to fetch info
        """
        res = client.force_login(hosting_user)
        res2 = client.get(reverse('admin:check_url'))

        res3 = client.post(reverse('admin:check_url'), {
                "url": "http://thegreenwebfoundation.org"
        })
        logger.info(f"greencheck: {res3.context.get('greencheck')}")
        logger.info(f"whois_check: {res3.context.get('whois_check')}")

        whois_check = res3.context.get('whois_check')

        assert 'green_status' in res3.context
        assert whois_check
