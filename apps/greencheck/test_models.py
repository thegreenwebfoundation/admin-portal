import pytest

import ipaddress

from apps.greencheck.models import GreencheckIp


class TestGreenCheckIP:

    def test_greencheckip_has_start_and_end(self, hosting_provider, db):
        hosting_provider.save()
        gcip = GreencheckIp.objects.create(
            active=True,
            ip_start="127.0.0.1",
            ip_end="120.0.0.1",
            hostingprovider=hosting_provider
        )
        gcip.save()

