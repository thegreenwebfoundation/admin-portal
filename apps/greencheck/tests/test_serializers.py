import ipaddress
import logging

import pytest
from hypothesis import given, strategies
from hypothesis.extra.django import from_model
from rest_framework import serializers

from apps.greencheck.models import GreencheckIp, GreencheckASN, Hostingprovider
from apps.greencheck.serializers import GreenIPRangeSerializer, GreenASNSerializer

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


@pytest.fixture
def new_hosting_provider():

    return Hostingprovider(
        archived=False,
        country="NL",
        customer=False,
        icon="",
        iconurl="",
        model="groeneenergie",
        name="Greeny Cloudy",
        partner="",
        showonwebsite=True,
        website="http://greeny.cloud",
    )


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

        for key in ["ip_start", "ip_end", "hostingprovider"]:
            assert key in keys

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

        for key in ["ip_start", "ip_end", "hostingprovider"]:
            assert key in keys

        assert data["ip_start"] == str(ip_addy_start)
        assert data["ip_end"] == str(ip_addy_end)
        assert data["hostingprovider"] == hosting_provider.id

    @pytest.mark.parametrize("ip_addy_start,ip_addy_end", SAMPLE_IPS)
    def test_green_ip_range_parses_and_saves(
        self, hosting_provider, db, ip_addy_start, ip_addy_end
    ):
        """
        Given the JSON representation can we deserialise this and store it in
        our database?
        """

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
            (
                "240.0.0.245",
                "240.0.0.1",
            ),
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


class TestGreenASNSerialiser:
    def test_deserialising_green_asn(self, hosting_provider, settings):
        """
        Can we take an Green ASN, and serialise it a form we serve over an
        API representation?
        """

        gc_asn = GreencheckASN(
            active=True,
            asn=12345,
            hostingprovider=hosting_provider,
        )
        gc_asn_serialized = GreenASNSerializer(gc_asn)
        data = gc_asn_serialized.data
        keys = data.keys()

        for key in ["asn", "hostingprovider"]:
            assert key in keys

        assert data["asn"] == gc_asn.asn
        assert data["hostingprovider"] == hosting_provider.id

    def test_green_asn_serializes_from_database(self, hosting_provider, db):
        """
        Can we make a ASN from provided JSON payload?
        """
        hosting_provider.save()

        sample_data = {
            "asn": 12345,
            "hostingprovider": hosting_provider.id,
        }

        gcn = GreenASNSerializer(data=sample_data)
        assert gcn.is_valid()

        gcn.save()
        created_asn, *_ = GreencheckASN.objects.filter(hostingprovider=hosting_provider)

        created_asn.asn == sample_data["asn"]
        created_asn.hostingprovider.id == sample_data["hostingprovider"]

    def test_asn_is_checked_as_a_valid_number(
        self, db, hosting_provider, new_hosting_provider
    ):
        # ASNs are always greater than 0
        # ASNs count up to 4294967295
        # https://www.arin.net/resources/guide/asn/

        # there are also some reserved AS Numbers we ought to be aware of
        # https://en.wikipedia.org/wiki/Autonomous_system_%28Internet%29

        hosting_provider.save()
        new_hosting_provider.save()

        sample_data = {
            "asn": 12345,
            "hostingprovider": hosting_provider.id,
        }

        gcn = GreenASNSerializer(data=sample_data)
        assert gcn.is_valid()

        gcn.save()

        second_sample_data = {
            "asn": 12345,
            "hostingprovider": new_hosting_provider.id,
        }
        second_gcn = GreenASNSerializer(data=second_sample_data)
        assert not second_gcn.is_valid()
