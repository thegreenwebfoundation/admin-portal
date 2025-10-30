import pytest

from apps.accounts import models as ac_models
from .. import models as gc_models

from .. import network_utils

class TestNetworkUTils:
    @pytest.mark.django_db
    def test_order_ip_range_by_size(
        self,
        hosting_provider: ac_models.Hostingprovider,
    ):
        hosting_provider.save()
        small_ip_range = gc_models.GreencheckIp.objects.create(
            active=True,
            ip_start="127.0.1.2",
            ip_end="127.0.1.3",
            hostingprovider=hosting_provider,
        )
        small_ip_range.save()

        large_ip_range = gc_models.GreencheckIp.objects.create(
            active=True,
            ip_start="127.0.1.2",
            ip_end="127.0.1.200",
            hostingprovider=hosting_provider,
        )
        large_ip_range.save()

        ip_matches = gc_models.GreencheckIp.objects.filter(
            ip_end__gte="127.0.1.2",
            ip_start__lte="127.0.1.2",
        )

        res = network_utils.order_ip_range_by_size(ip_matches)

        assert res[0].ip_end == "127.0.1.3"

