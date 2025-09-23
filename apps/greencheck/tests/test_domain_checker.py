import ipaddress
import logging
import socket
from unittest import mock

import pytest

from apps.accounts import models as ac_models

from .. import domain_check, legacy_workers
from .. import models as gc_models

pytestmark = pytest.mark.django_db

logger = logging.getLogger(__name__)


@pytest.fixture
def checker():
    return domain_check.GreenDomainChecker()

class TestDomainChecker:

    @mock.patch("apps.greencheck.domain_check.ProviderCarbonTxt")
    def test_with_green_domain_by_carbon_txt(self, provider_carbon_txt_mock, checker, provider_carbon_txt_factory):
        """
        Given a domain with a valid carbon.txt and unarchived provider,
        do we return a green sitecheck?
        """

        carbon_txt = provider_carbon_txt_factory(domain="example.com")
        provider_carbon_txt_mock.find_for_domain.return_value = carbon_txt

        res = checker.check_domain("example.com")

        assert isinstance(res, legacy_workers.SiteCheck)
        assert res.match_type == "carbontxt"
        assert res.green


    @mock.patch("apps.greencheck.domain_check.ProviderCarbonTxt")
    def test_with_grey_domain_by_invalid_carbon_txt(self, provider_carbon_txt_mock, checker, provider_carbon_txt_factory):
        """
        Given a domain with an invalid carbon.txt and unarchived provider,
        do we return a grey sitecheck?
        """

        carbon_txt = provider_carbon_txt_factory(domain="example.com", carbon_txt_url=None)
        provider_carbon_txt_mock.find_for_domain.return_value = carbon_txt

        res = checker.check_domain("example.com")

        assert isinstance(res, legacy_workers.SiteCheck)
        assert res.match_type == "ip"
        assert not res.green

    @mock.patch("apps.greencheck.domain_check.ProviderCarbonTxt")
    def test_with_grey_domain_by_valid_carbon_txt_with_archived_provider(self, provider_carbon_txt_mock, checker, provider_carbon_txt_factory):
        """
        Given a domain with a valid carbon.txt and archived provider,
        do we return a grey sitecheck?
        """

        carbon_txt = provider_carbon_txt_factory(domain="example.com")
        carbon_txt.provider.archived = True
        carbon_txt.provider.save()

        provider_carbon_txt_mock.find_for_domain.return_value = carbon_txt

        res = checker.check_domain("example.com")

        assert isinstance(res, legacy_workers.SiteCheck)
        assert res.match_type == "ip"
        assert not res.green


    def test_with_green_domain_by_ip(self, green_ip, checker):
        """
        Given a matching IP, do we return a green sitecheck?
        """

        res = checker.check_domain("172.217.168.238")

        assert isinstance(res, legacy_workers.SiteCheck)
        assert res.ip in (green_ip.ip_start, green_ip.ip_end)

    # this came out of a discussion with the folks at mythic beasts
    # who have some ipv6 only domains. If we need to mock it in future,
    # we can
    @pytest.mark.parametrize(
        "domain",
        [
            "ipv6.api.mythic-beasts.com",
            "ipv4.api.mythic-beasts.com",
        ],
    )
    def test_domain_to_ip_supports_ipv4_and_ipv6(self, checker, domain):
        """
        When we check a a domain that resolves to an IPv6 address
        Do we get the appropriate response back?
        """
        res = checker.convert_domain_to_ip(domain)

        assert isinstance(res, ipaddress.IPv6Address) or isinstance(
            res, ipaddress.IPv4Address
        )

    @pytest.mark.parametrize(
        "domain",
        [
            "defintely-not-a-valid-domain",
            "valid-domain-but-not-resolving.com",
        ],
    )
    def test_domain_to_ip_does_not_fail_silently(self, checker, domain):
        """
        When we check a domain that does not resolve successfully, are we
        notified so we can catch exception appropriately?
        """

        with pytest.raises((ipaddress.AddressValueError, socket.gaierror)):
            checker.convert_domain_to_ip(domain)

    def test_with_green_domain_by_asn(self, green_asn, checker):
        """
        Given a matching ASN, do we return a green sitecheck?
        """
        green_asn.save()

        # mock response for GreenDomainChecker.asn_from_ip, to avoid
        # making dns lookups
        checker.asn_from_ip = mock.MagicMock(return_value=green_asn.asn)

        res = checker.check_domain("172.217.168.238")

        assert isinstance(res, legacy_workers.SiteCheck)
        assert res.hosting_provider_id == green_asn.hostingprovider.id

    def test_with_grey_domain(self, checker):
        """
        Do we get a regular grey sitecheck result if we have no matches?
        """
        res = checker.check_domain("172.217.168.238")

        assert isinstance(res, legacy_workers.SiteCheck)
        assert res.green is False
        assert res.url == "172.217.168.238"
        assert res.ip == "172.217.168.238"

    def test_with_green_domain_by_asn_double(self, green_asn, checker):
        """ """
        green_asn.save()
        checker.asn_from_ip = mock.MagicMock(return_value=f"{green_asn.asn} 12345")

        res = checker.check_domain("172.217.168.238")

        assert isinstance(res, legacy_workers.SiteCheck)
        assert res.hosting_provider_id == green_asn.hostingprovider.id

    @pytest.mark.parametrize(
        "error_type",
        (
            domain_check.ASNLookupError,
            domain_check.ASNParseError,
            domain_check.ASNRegistryError,
            domain_check.ASNOriginLookupError,
            domain_check.IPDefinedError,
        ),
    )
    def test_asn_from_ip_fails_gracefully_with_bad_asn_lookup(
        self, checker, caplog, error_type
    ):
        """
        Sometimes calling lookup() on an IP address raises a ASNParseError.
        Do we catch this exception and log it?
        """

        checker.asn_from_ip = mock.MagicMock(side_effect=error_type)
        with caplog.at_level(logging.WARNING):
            res = checker.check_for_matching_asn("23.32.24.203")

        assert res is False
        logged_error = caplog.text

        assert error_type.__name__ in logged_error

    def test_with_green_domain_by_non_resolving_asn(self, green_asn, checker):
        """
        Sometimes the service we use for resolving ASNs returns
        an empty result.
        """
        green_asn.save()
        checker.asn_from_ip = mock.MagicMock(return_value=None)

        res = checker.check_domain("100.113.75.254")

        assert isinstance(res, legacy_workers.SiteCheck)


class TestDomainCheckerCarbonTxtCacheBehaviour:


    @mock.patch("apps.accounts.models.hosting.carbon_txt.ProviderCarbonTxt")
    def test_with_cached_green_domain_by_carbon_txt(self, provider_carbon_txt_mock, checker, provider_carbon_txt_factory):
        """
        WHEN I query a domain with a valid carbon.txt and unarchived provider,
        AND I do not explicitly refresh the domain cache
        THEN the cached carbon.txt result should be used.
        """

        carbon_txt = provider_carbon_txt_factory(domain="example.com")
        provider_carbon_txt_mock._find_for_domain_uncached.return_value = carbon_txt

        checker.check_domain("example.com")

        old_modified = ac_models.CarbonTxtDomainResultCache.objects.filter(domain="example.com").first().modified

        checker.check_domain("example.com")

        new_modified = ac_models.CarbonTxtDomainResultCache.objects.filter(domain="example.com").first().modified

        assert old_modified == new_modified

    @mock.patch("apps.accounts.models.hosting.carbon_txt.ProviderCarbonTxt")
    def test_with_uncached_green_domain_by_carbon_txt(self, provider_carbon_txt_mock, checker, provider_carbon_txt_factory):
        """
        WHEN I query a domain with a valid carbon.txt and unarchived provider,
        AND I do explicitly refresh the domain cache
        THEN the cached carbon.txt result should not be used.
        """

        carbon_txt = provider_carbon_txt_factory(domain="example.com")
        provider_carbon_txt_mock._find_for_domain_uncached.return_value = carbon_txt

        checker.check_domain("example.com")

        old_modified = ac_models.CarbonTxtDomainResultCache.objects.filter(domain="example.com").first().modified

        checker.check_domain("example.com", refresh_carbon_txt_cache=True)

        new_modified = ac_models.CarbonTxtDomainResultCache.objects.filter(domain="example.com").first().modified

        assert old_modified < new_modified

    def test_with_cached_grey_domain_by_carbon_txt(self, checker):
        """
        WHEN I query a domain without a valid carbon.txt,
        AND I do not explicitly refresh the domain cache
        THEN the cached null carbon.txt result should be used.
        """

        checker.check_domain("example.com")

        old_modified = ac_models.CarbonTxtDomainResultCache.objects.filter(domain="example.com").first().modified

        checker.check_domain("example.com")

        new_modified = ac_models.CarbonTxtDomainResultCache.objects.filter(domain="example.com").first().modified

        assert old_modified == new_modified

    def test_with_uncached_grey_domain_by_carbon_txt(self, checker):
        """
        WHEN I query a domain without a valid carbon.txt,
        AND I do explicitly refresh the domain cache
        THEN the cached null carbon.txt result should not be used.
        """

        checker.check_domain("example.com")

        old_modified = ac_models.CarbonTxtDomainResultCache.objects.filter(domain="example.com").first().modified

        checker.check_domain("example.com", refresh_carbon_txt_cache=True)

        new_modified = ac_models.CarbonTxtDomainResultCache.objects.filter(domain="example.com").first().modified

        assert old_modified < new_modified



class TestDomainCheckerOrderBySize:
    """
    Check that we can return the ip ranges from a check in the
    ascending correct order of size.
    """

    def test_order_ip_range_by_size(
        self,
        hosting_provider: ac_models.Hostingprovider,
        checker: domain_check.GreenDomainChecker,
        db,
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

        res = checker.order_ip_range_by_size(ip_matches)

        assert res[0].ip_end == "127.0.1.3"

    def test_return_org_with_smallest_ip_range_first(
        self,
        hosting_provider: ac_models.Hostingprovider,
        checker: domain_check.GreenDomainChecker,
        db,
    ):
        """
        When we have two hosting providers, where one provider is using a
        subset of larger provider's IP range, we return the smaller
        provider first. This allows resellers to be visible.
        """

        hosting_provider.save()

        large_ip_range = gc_models.GreencheckIp.objects.create(
            active=True,
            ip_start="127.0.1.2",
            ip_end="127.0.1.200",
            hostingprovider=hosting_provider,
        )
        large_ip_range.save()

        small_hosting_provider = ac_models.Hostingprovider(
            archived=False,
            country="US",
            customer=False,
            icon="",
            iconurl="",
            model="groeneenergie",
            name="Smaller Reseller",
            partner="",
            is_listed=True,
            website="http://small-reseller.com",
        )
        small_hosting_provider.save()

        small_ip_range = gc_models.GreencheckIp.objects.create(
            active=True,
            ip_start="127.0.1.2",
            ip_end="127.0.1.3",
            hostingprovider=small_hosting_provider,
        )
        small_ip_range.save()

        res = checker.check_domain("127.0.1.2")

        assert res.hosting_provider_id == small_hosting_provider.id


class TestDomainCheckByCarbonTxt:
    """Test that lookups via carbon txt work as expected"""

    def test_lookup_green_domain(
        self, green_domain_factory, green_ip_factory, mocker, checker
    ):
        # mock our network lookup, so we get a consistent response when
        # looking up our domains
        green_ip = green_ip_factory.create()

        # mock our request to avoid the network call
        mocker.patch(
            "apps.greencheck.domain_check.GreenDomainChecker.convert_domain_to_ip",
            return_value=green_ip.ip_start,
        )

        domain = green_domain_factory.create(hosted_by=green_ip.hostingprovider)
        provider = domain.hosting_provider

        # look up for domain.com
        res = checker.check_domain(domain.url)

        # check that we return the provider in the return value
        assert res.hosting_provider_id == provider.id

    def test_lookup_green_domain_with_no_provider(
        self, green_domain_factory, green_ip_factory, mocker, checker
    ):
        """
        When a domain has no provider, do we still return none?
        """
        green_ip = green_ip_factory.create()

        # mock our request to avoid the network call
        mocker.patch(
            "apps.greencheck.domain_check.GreenDomainChecker.convert_domain_to_ip",
            return_value=green_ip.ip_start,
        )

        domain = green_domain_factory.create(hosted_by=green_ip.hostingprovider)
        domain.hosting_provider.delete()
        domain.save()

        # look up for domain.com
        res = checker.check_domain(domain.url)

        # check that we get a response back and a grey result,
        # as there is no evidence left to support the green result
        assert res.green is False

    def test_lookup_green_domain_with_no_ip_lookup(
        self, green_domain_factory, green_ip_factory, mocker, checker
    ):
        """"""
        green_ip_factory.create()

        # mock our request to avoid the network call
        # mocker.patch(
        #     "apps.greencheck.domain_check.GreenDomainChecker.convert_domain_to_ip",
        #     return_value=green_ip.ip_start,
        # )

        # domain = green_domain_factory.create(hosted_by=green_ip.hostingprovider)
        # domain.hosting_provider.delete()
        # domain.save()

        # look up for domain.com
        res = checker.check_domain("portail.numerique-educatif.fr")

        from apps.greencheck.workers import SiteCheckLogger

        # saving with None fails, as does "None", but passing 0 works,
        # and we want to log the fact that a check took place, instead
        # of silently erroring
        # res.ip = 0

        site_logger = SiteCheckLogger()
        site_logger.log_sitecheck_to_database(res)
        # check that we get a response back and a grey result,
        # as there is no evidence left to support the green result
        assert res.green is False
