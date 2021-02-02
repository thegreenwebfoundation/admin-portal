import ipaddress
import logging

import pytest
from hypothesis import given, strategies
from hypothesis.extra.django import from_model
from rest_framework import serializers

from apps.greencheck.models import GreencheckIp
from apps.greencheck.serializers import GreenIPRangeSerializer

logger = logging.getLogger(__name__)

SAMPLE_IPS = [
    # ipv4
    ("240.0.0.1", "240.0.0.245"),
    # ipv6
    (
        "3e5c:a68a:9dbe:c49a:6884:943f:7c71:21dd",
        "3e5c:a68a:9dbe:c49a:6884:943f:7c71:27dd",
    ),
]


@pytest.mark.only
class TestGreenIpRangeSerialiser:
    # @given(
    #     ip_addy_start=strategies.ip_addresses(), ip_addy_end=strategies.ip_addresses()
    # )
    # @pytest.mark.skip(reason="Our serialiser needs to this the database, but ")
    @pytest.mark.parametrize("ip_addy_start,ip_addy_end", SAMPLE_IPS)
    def test_deserialising_green_ip_range(
        self, hosting_provider, ip_addy_start, ip_addy_end, settings
    ):

        # uncomment this to check ip ranges we're generating and testing
        # logger.info(f"start_ip:  {ip_addy_start}, end_ip: {ip_addy_end}")

        gcip = GreencheckIp(
            active=True,
            ip_start=str(ip_addy_start),
            ip_end=str(ip_addy_end),
            hostingprovider=hosting_provider,
        )
        gipr = GreenIPRangeSerializer(gcip)
        data = gipr.data
        keys = data.keys()

        for key in ["active", "ip_start", "ip_end", "hostingprovider"]:
            assert key in keys

        assert data["active"] == True
        assert data["ip_start"] == str(ip_addy_start)
        assert data["ip_end"] == str(ip_addy_end)
        assert data["hostingprovider"] == hosting_provider.id

    @pytest.mark.parametrize("ip_addy_start,ip_addy_end", SAMPLE_IPS)
    def test_green_iprange_serializes_from_database(
        self, hosting_provider, ip_addy_start, ip_addy_end, db
    ):
        """
        Check that these work when fetching data from the database too.
        """
        hosting_provider.save()

        gcip = GreencheckIp.objects.create(
            active=True,
            ip_start=ip_addy_start,
            ip_end=ip_addy_end,
            hostingprovider=hosting_provider,
        )
        gcip.save()
        gipr = GreenIPRangeSerializer(gcip)
        data = gipr.data
        keys = data.keys()

        for key in ["active", "ip_start", "ip_end", "hostingprovider"]:
            assert key in keys

        assert data["active"] == True
        assert data["ip_start"] == str(ip_addy_start)
        assert data["ip_end"] == str(ip_addy_end)
        assert data["hostingprovider"] == hosting_provider.id

    @pytest.mark.parametrize("ip_addy_start,ip_addy_end", SAMPLE_IPS)
    def test_green_ip_range_parses_and_saves(
        self, hosting_provider, db, ip_addy_start, ip_addy_end
    ):

        assert GreencheckIp.objects.count() == 0
        hosting_provider.save()

        sample_json = {
            "hostingprovider": hosting_provider.id,
            "ip_start": str(ip_addy_start),
            "ip_end": str(ip_addy_end),
        }

        gipr = GreenIPRangeSerializer(data=sample_json)
        gipr.is_valid()
        data = gipr.save()

        assert data.ip_start == ipaddress.ip_address(ip_addy_start)
        assert data.ip_end == ipaddress.ip_address(ip_addy_end)
        assert data.hostingprovider == hosting_provider

    @pytest.mark.parametrize(
        "ip_addy_start,ip_addy_end",
        [
            # ipv4
            ("240.0.0.245", "240.0.0.1",),
            # ipv6
            (
                "3e5c:a68a:9dbe:c49a:6884:943f:7c71:27dd",
                "3e5c:a68a:9dbe:c49a:6884:943f:7c71:21dd",
            ),
        ],
    )
    def test_green_ip_range_parser_catches_inverted_ranges(
        self, hosting_provider, db, ip_addy_start, ip_addy_end
    ):
        """
        Make sure that our serialise catches when people submit an
        IP range where the start of the range is higher than the end
        """

        hosting_provider.save()

        sample_json = {
            "hostingprovider": hosting_provider.id,
            "ip_start": str(ip_addy_start),
            "ip_end": str(ip_addy_end),
        }

        gipr = GreenIPRangeSerializer(data=sample_json)

        with pytest.raises(serializers.ValidationError):
            gipr.is_valid(raise_exception=True)
