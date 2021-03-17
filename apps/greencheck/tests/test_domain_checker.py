import logging
import pytest


from .. import legacy_workers
from .. import domain_check
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
        """
        """
        green_asn.save()
        checker.asn_from_ip = mock.MagicMock(return_value=f"{green_asn.asn} 12345")

        res = checker.check_domain("172.217.168.238")

        assert isinstance(res, legacy_workers.SiteCheck)
        assert res.hosting_provider_id == green_asn.hostingprovider.id
