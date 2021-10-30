import logging
from . import view_in_browser

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from .. import models as gc_models
from ...accounts import models as ac_models

User = get_user_model()

pytestmark = pytest.mark.django_db

logger = logging.getLogger(__name__)


class TestGreencheckTryout:
    """
    A test to check that our try out view returns
    enough info for debugging.

    If you run a detailed check, you want to see the kind of match made, and if
    not, some any information that would suggest the IP Network or ASN and
    domain's ip belongs to, along with anything we might clean from a whois lookup.
    """

    def test_tryout_returns_green_ip_match(
        self, hosting_provider_with_sample_user: ac_models.Hostingprovider,
        green_ip: gc_models.GreencheckIp,
        client,
    ):
    
        # do we have a green match?
        logger.info(green_ip)

        #  are we able to access the tryout url?
        tryout_path = reverse("admin:check_url")
        res = client.get(tryout_path, follow=True)
        assert res.status_code == 200
        

        # can we see a positive match in the template?
        