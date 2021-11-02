import logging
import pytest


from .. import legacy_workers
from .. import domain_check
from .. import models as gc_models
from apps.accounts import models as ac_models
from unittest import mock

pytestmark = pytest.mark.django_db

logger = logging.getLogger(__name__)


@pytest.fixture
def checker():
    return domain_check.GreenDomainChecker()


class TestDomainChecker:
    def test_with_green_domain_by_ip(self, green_ip, checker):
        """
        Given a matching IP, do we return a green sitecheck?
        """

        res = checker.check_domain("172.217.168.238")

        assert isinstance(res, legacy_workers.SiteCheck)
        assert res.ip in (green_ip.ip_start, green_ip.ip_end)

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

    def test_with_green_domain_by_non_resolving_asn(self, green_asn, checker):
        """
        Sometimes the service we use for resolving ASNs returns
        an empty result.
        """
        green_asn.save()
        checker.asn_from_ip = mock.MagicMock(return_value=None)

        res = checker.check_domain("100.113.75.254")

        assert isinstance(res, legacy_workers.SiteCheck)


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
            showonwebsite=True,
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
        self,
    ):

        # check that we have a green domain for domain.com

        # look up for domain.com

        # check that we return the provider in the return value
        pass

    def test_lookup_green_domain_with_no_provider(self):
        """
        When a domain has no provider, do we still return none?
        """

        # check that we have a green domain for domain.com

        # look up for domain.com

        # check that we return None, without raising an exception
        pass
