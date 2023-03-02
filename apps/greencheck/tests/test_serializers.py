import ipaddress
import logging

import pytest
import pathlib
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from rest_framework import serializers


from ...accounts import models as ac_models
from .. import legacy_workers
from .. import models as gc_models
from .. import serializers as gc_serializers
from . import greencheck_sitecheck
from .. import carbon_txt

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
def carbon_txt_string():
    pth = pathlib.Path(__file__)

    carbon_txt_path = pth.parent / "carbon-txt-samples" / "carbon-txt-test.toml"

    carbon_txt_string = None
    with open(carbon_txt_path) as carb_file:
        carbon_txt_string = carb_file.read()

    return carbon_txt_string


@pytest.fixture
def new_hosting_provider():
    return ac_models.Hostingprovider(
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

        gcip = gc_models.GreencheckIp(
            active=True,
            ip_start=str(ip_addy_start),
            ip_end=str(ip_addy_end),
            hostingprovider=hosting_provider,
        )
        gipr = gc_serializers.GreenIPRangeSerializer(gcip)
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

        gcip = gc_models.GreencheckIp.objects.create(
            active=True,
            ip_start=ip_addy_start,
            ip_end=ip_addy_end,
            hostingprovider=hosting_provider,
        )
        gcip.save()
        gipr = gc_serializers.GreenIPRangeSerializer(gcip)
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

        assert gc_models.GreencheckIp.objects.count() == 0
        hosting_provider.save()

        sample_json = {
            "hostingprovider": hosting_provider.id,
            "ip_start": str(ip_addy_start),
            "ip_end": str(ip_addy_end),
        }

        gipr = gc_serializers.GreenIPRangeSerializer(data=sample_json)
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

        gipr = gc_serializers.GreenIPRangeSerializer(data=sample_json)

        with pytest.raises(serializers.ValidationError):
            gipr.is_valid(raise_exception=True)


class TestGreenASNSerialiser:
    def test_deserialising_green_asn(self, hosting_provider, settings):
        """
        Can we take an Green ASN, and serialise it a form we serve over an
        API representation?
        """

        gc_asn = gc_models.GreencheckASN(
            active=True,
            asn=12345,
            hostingprovider=hosting_provider,
        )
        gc_asn_serialized = gc_serializers.GreenASNSerializer(gc_asn)
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

        gcn = gc_serializers.GreenASNSerializer(data=sample_data)
        assert gcn.is_valid()

        gcn.save()
        created_asn, *_ = gc_models.GreencheckASN.objects.filter(
            hostingprovider=hosting_provider
        )

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

        gcn = gc_serializers.GreenASNSerializer(data=sample_data)
        assert gcn.is_valid()

        gcn.save()

        second_sample_data = {
            "asn": 12345,
            "hostingprovider": new_hosting_provider.id,
        }
        second_gcn = gc_serializers.GreenASNSerializer(data=second_sample_data)
        assert not second_gcn.is_valid()


class TestGreenDomainSerialiser:
    def test_serialising_green_domain_with_evidence(
        self, db, hosting_provider, green_ip
    ):
        """
        Can we get a usable JSON representation of a green domain,
        with supporting evidence included?
        """
        hosting_provider.save()
        domain = "google.com"
        sitecheck_logger = legacy_workers.LegacySiteCheckLogger()

        now = timezone.now()
        a_year_from_now = now + relativedelta(years=1)

        #  create supporting evidence for hosting provider
        supporting_doc = ac_models.HostingProviderSupportingDocument.objects.create(
            hostingprovider=hosting_provider,
            title="Carbon free energy for Google Cloud regions",
            url="https://cloud.google.com/sustainability/region-carbon",
            description=(
                "Google's guidance on understanding how they "
                "power each region, how they acheive carbon free "
                "energy, and how to report it"
            ),
            valid_from=now,
            valid_to=a_year_from_now,
            public=True,
        )

        sitecheck = greencheck_sitecheck(domain, hosting_provider, green_ip)
        sitecheck_logger.update_green_domain_caches(sitecheck, hosting_provider)

        # save a doamin as belonging to a provider
        green_dom = gc_models.GreenDomain.objects.all().first()
        serialized_green_dom = gc_serializers.GreenDomainSerializer(green_dom)

        # check that the domain, if it has hosting provider
        # also lists the public evidence
        assert len(serialized_green_dom.data["supporting_documents"])

        docs = serialized_green_dom.data["supporting_documents"]
        assert docs[0]["link"] == supporting_doc.url
        assert docs[0]["title"] == supporting_doc.title


class TestCarbonTxtSerializer:
    def test_serialising_carbon_txt(
        self,
        db,
        carbon_txt_string,
        hosting_provider_factory,
        supporting_evidence_factory,
        green_domain_factory,
    ):
        """Check our seriliasation works"""
        provider = hosting_provider_factory.create(
            name="www.hillbob.de", website="https://www.hillbob.de"
        )
        supporting_evidence_factory.create(hostingprovider=provider)

        # create our upstream providers
        systen_upstream = hosting_provider_factory.create(
            name="sys-ten.com", website="https://sys-ten.com"
        )
        supporting_evidence_factory.create(
            hostingprovider=systen_upstream,
            url="https://www.sys-ten.de/en/about-us/our-data-centers/",
        )

        cdn_upstream = hosting_provider_factory.create(
            name="cdn.com", website="https://cdn.com"
        )
        supporting_evidence_factory.create(
            hostingprovider=cdn_upstream,
            url="https://cdn.com/company/corporate-responsibility/sustainability",
        )

        # create our domains we use to look up each provider
        green_domain_factory.create(hosted_by=provider, url="www.hillbob.de")
        green_domain_factory.create(hosted_by=systen_upstream, url="sys-ten.com")
        green_domain_factory.create(hosted_by=cdn_upstream, url="cdn.com")

        psr = carbon_txt.CarbonTxtParser()
        result = psr.parse("www.hillbob.de", carbon_txt_string)

        res = gc_serializers.CarbonTxtSerializer(result)
        for key in ["org", "upstream", "not_registered"]:
            assert key in res.data.keys()

        assert len(res.data["upstream"]) == 2
        assert len(res.data["not_registered"]) == 2
