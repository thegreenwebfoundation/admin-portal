import pytest

import logging

console = logging.StreamHandler()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(console)

from apps.greencheck.legacy_workers import LegacySiteCheckLogger, SiteCheck
from apps.greencheck.models import Greencheck, GreenDomain
from apps.accounts.models import Hostingprovider


@pytest.fixture
def serialised_php():
    return b'a:1:{s:6:"result";O:31:"TGWF\\Greencheck\\SitecheckResult":10:{s:43:"\x00TGWF\\Greencheck\\SitecheckResult\x00checkedUrl";s:10:"google.com";s:42:"\x00TGWF\\Greencheck\\SitecheckResult\x00checkedAt";O:8:"DateTime":3:{s:4:"date";s:26:"2021-01-19 08:04:59.106883";s:13:"timezone_type";i:3;s:8:"timezone";s:3:"UTC";}s:38:"\x00TGWF\\Greencheck\\SitecheckResult\x00green";b:1;s:37:"\x00TGWF\\Greencheck\\SitecheckResult\x00data";b:1;s:39:"\x00TGWF\\Greencheck\\SitecheckResult\x00cached";b:1;s:50:"\x00TGWF\\Greencheck\\SitecheckResult\x00idHostingProvider";i:595;s:48:"\x00TGWF\\Greencheck\\SitecheckResult\x00hostingProvider";O:38:"TGWF\\Greencheck\\Entity\\Hostingprovider":14:{s:5:"\x00*\x00id";i:595;s:7:"\x00*\x00naam";s:11:"Google Inc.";s:10:"\x00*\x00website";s:14:"www.google.com";s:8:"\x00*\x00model";s:13:"groeneenergie";s:16:"\x00*\x00countrydomain";s:2:"US";s:11:"\x00*\x00customer";b:0;s:7:"\x00*\x00icon";s:0:"";s:10:"\x00*\x00iconurl";s:0:"";s:16:"\x00*\x00showonwebsite";b:0;s:15:"\x00*\x00certificates";N;s:12:"\x00*\x00asnumbers";O:43:"Doctrine\\Common\\Collections\\ArrayCollection":1:{s:53:"\x00Doctrine\\Common\\Collections\\ArrayCollection\x00elements";a:0:{}}s:12:"\x00*\x00iprecords";O:43:"Doctrine\\Common\\Collections\\ArrayCollection":1:{s:53:"\x00Doctrine\\Common\\Collections\\ArrayCollection\x00elements";a:0:{}}s:20:"\x00*\x00greencheckrecords";O:43:"Doctrine\\Common\\Collections\\ArrayCollection":1:{s:53:"\x00Doctrine\\Common\\Collections\\ArrayCollection\x00elements";a:0:{}}s:47:"\x00TGWF\\Greencheck\\Entity\\Hostingprovider\x00partner";N;}s:35:"\x00TGWF\\Greencheck\\SitecheckResult\x00ip";a:2:{s:4:"ipv4";s:14:"172.217.21.238";s:4:"ipv6";b:0;}s:42:"\x00TGWF\\Greencheck\\SitecheckResult\x00matchtype";a:3:{s:2:"id";i:198;s:4:"type";s:2:"as";s:10:"identifier";i:15169;}s:43:"\x00TGWF\\Greencheck\\SitecheckResult\x00calledfrom";a:3:{s:10:"checked_by";s:9:"127.0.0.1";s:15:"checked_browser";s:82:"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:85.0) Gecko/20100101 Firefox/85.0";s:15:"checked_through";s:3:"api";}}}'


@pytest.fixture
def sitecheck_logger():
    return LegacySiteCheckLogger()


class TestSiteCheckConsumerParsePHP:
    def test_parse_serialsed_php_from_bytes(self, sitecheck_logger, serialised_php):
        """
        Can we parse the serialised php so we have it in a form we can
        manipulate.
        """
        result = sitecheck_logger.parse_serialised_php(serialised_php)

        assert isinstance(result, dict)

    def test_return_dict_fromp_phpobject(self, sitecheck_logger, serialised_php):
        result = sitecheck_logger.sitecheck_from_php_dict(serialised_php)

        assert isinstance(result, SiteCheck)

        assert result.ip == "172.217.21.238"
        assert result.url == "google.com"
        assert result.data == True
        assert result.green == True
        assert result.hosting_provider_id == 595
        assert result.match_type == "as"
        assert result.match_ip_range == 198
        assert result.checked_at == "2021-01-19 08:04:59"

    @pytest.mark.parametrize(
        "key,val",
        (
            ("checkedUrl", "google.com"),
            ("green", True),
            ("data", True),
            ("cached", True),
            ("ip", "172.217.21.238"),
            ("idHostingProvider", 595),
            ("matchtype", {"id": 198, "type": "as", "identifier": 15169}),
            ("checkedAt", "2021-01-19 08:04:59"),
        ),
    )
    def test_fetch_namespaced_key(self, sitecheck_logger, serialised_php, key, val):

        result = sitecheck_logger.parse_serialised_php(serialised_php)
        fetched_val = sitecheck_logger.prefixed_attr(key)
        assert fetched_val == val

    def test_logging_database(self, db, sitecheck_logger, serialised_php):

        Hostingprovider.objects.create(
            id=595,
            archived=False,
            country="US",
            customer=False,
            icon="",
            iconurl="",
            model="groeneenergie",
            name="Google",
            partner="",
            showonwebsite=True,
            website="http://google.com",
        )

        assert Greencheck.objects.count() == 0
        assert GreenDomain.objects.count() == 0

        sitecheck_logger.parse_and_log_to_database(serialised_php)

        assert Greencheck.objects.count() == 1
        assert GreenDomain.objects.count() == 1

    @pytest.mark.parametrize(
        "green, hosting_provider_id, green_domain_count, greencheck_ip_range_id, greencheck_match_type",
        (
            (True, 595, 1, 198, "as"),
            (True, 595, 1, 0, "url"),
            (False, None, 0, 0, "none"),
        ),
    )
    def test_logging_sitecheck(
        self,
        db,
        sitecheck_logger,
        sample_sitecheck,
        green,
        hosting_provider_id,
        green_domain_count,
        greencheck_ip_range_id,
        greencheck_match_type,
    ):
        Hostingprovider.objects.create(
            id=595,
            archived=False,
            country="US",
            customer=False,
            icon="",
            iconurl="",
            model="groeneenergie",
            name="Google",
            partner="",
            showonwebsite=True,
            website="http://google.com",
        )

        assert Greencheck.objects.count() == 0
        assert GreenDomain.objects.count() == 0

        sample_sitecheck.green = green
        sample_sitecheck.hosting_provider_id = hosting_provider_id
        sample_sitecheck.match_ip_range = greencheck_ip_range_id
        sample_sitecheck.match_type = greencheck_match_type
        logger.debug(sample_sitecheck)

        sitecheck_logger.log_sitecheck_to_database(sample_sitecheck)

        assert Greencheck.objects.count() == 1
        assert GreenDomain.objects.count() == green_domain_count
