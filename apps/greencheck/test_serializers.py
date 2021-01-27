import pytest

import ipaddress

from apps.greencheck.models import GreencheckIp
from apps.greencheck.serializers import GreenIPRange
import logging
logger = logging.getLogger(__name__)


@pytest.mark.only
class TestGreenCheckIP:

    def test_green_iprange_serialises(self, hosting_provider, db):
        hosting_provider.save()
        gcip = GreencheckIp.objects.create(
            active=True,
            ip_start="120.0.0.1",
            ip_end="127.0.0.1",
            hostingprovider=hosting_provider
        )
        gcip.save()
        gipr = GreenIPRange(gcip)
        data = gipr.data
        keys = data.keys()

        for key in ['active', 'ip_start', 'ip_end', 'hostingprovider']:
            assert key in keys

        assert data['active'] == True
        assert data['ip_start'] == "120.0.0.1"
        assert data['ip_end'] == "127.0.0.1"

    @pytest.mark.parametrize("ip_start,ip_end", [
        # ipv4
        ("120.0.0.1", "127.0.0.1",),
        # ipv7
        ("120.0.0.1", "127.0.0.1",),
    ])
    def test_green_iprange_parses(self, hosting_provider, db, ip_start, ip_end):

            assert GreencheckIp.objects.count() == 0
            hosting_provider.save()

            sample_json = {
                "hostingprovider": hosting_provider.id,
                "ip_start": ip_start,
                "ip_end": ip_end,
                "active": True
            }


            gipr = GreenIPRange(data=sample_json)
            gipr.is_valid()
            logger.info(gipr.errors)
            data = gipr.save()

            assert GreencheckIp.objects.count() == 1
            
            assert data.active == True
            assert data.ip_end == ipaddress.ip_address(ip_end)
            assert data.ip_start == ipaddress.ip_address(ip_start)
            assert data.hostingprovider == hosting_provider
