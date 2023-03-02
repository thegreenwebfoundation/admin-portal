import pytest
import pathlib

from apps.accounts.models.hosting import Hostingprovider


from .. import carbon_txt
from ...accounts import models as ac_models
from .. import models as gc_models
from .. import choices
from .. import workers


@pytest.fixture
def carbon_txt_string():
    pth = pathlib.Path(__file__)

    carbon_txt_path = pth.parent / "carbon-txt-samples" / "carbon-txt-test.toml"

    carbon_txt_string = None
    with open(carbon_txt_path) as carb_file:
        carbon_txt_string = carb_file.read()

    return carbon_txt_string


@pytest.fixture
def shorter_carbon_txt_string():
    """use a minimal carbon.txt file"""

    short_string = """
        [upstream]
        providers = [
        'sys-ten.com',
        'cdn.com',
        ]
        [org]
        credentials = [
            { doctype = 'sustainability-page', url = 'https://www.hillbob.de/klimaneutral'}
        ]
    """  # noqa
    return short_string


class TestCarbonTxtParser:
    """
    First tests to check that we can parse the carbon.txt file
    """

    def test_parse_basic_provider(self, db, carbon_txt_string):
        """
        Has this created the necessary organisations?
        i.e. one hosting provider and the two upstream providers?
        And do they have the supporting info?
        """

        psr = carbon_txt.CarbonTxtParser()
        result = psr.parse_and_import("www.hillbob.de", carbon_txt_string)

        # do we have the 16 providers listed now?
        providers = ac_models.Hostingprovider.objects.all()

        assert len(providers) == 16
        assert len(result["upstream"]["providers"]) == 2
        assert len(result["org"]["providers"]) == 14

        # do the providers have any supporting evidence
        upstream_providers = result["org"]["providers"]
        org_providers = result["org"]["providers"]

        for prov in [*upstream_providers, *org_providers]:
            # is there at least one piece of supporting evidence
            # from the carbon txt file?
            assert prov.supporting_documents.all()

    def test_parse_basic_provider_without_import(
        self,
        db,
        carbon_txt_string,
        hosting_provider_factory,
        supporting_evidence_factory,
        green_domain_factory,
    ):
        # create our main org hosting the carbon.txt file
        provider = hosting_provider_factory.create(
            name="www.hillbob.de", website="https://www.hillbob.de"
        )
        sustainablity_page = supporting_evidence_factory.create(
            hostingprovider=provider
        )

        # create our upstream providers
        systen_upstream = hosting_provider_factory.create(
            name="sys-ten.com", website="https://sys-ten.com"
        )
        systen_sustainability_page = supporting_evidence_factory.create(
            hostingprovider=systen_upstream,
            url="https://www.sys-ten.de/en/about-us/our-data-centers/",
        )

        cdn_upstream = hosting_provider_factory.create(
            name="cdn.com", website="https://cdn.com"
        )
        cdn_sustainability_page = supporting_evidence_factory.create(
            hostingprovider=cdn_upstream,
            url="https://cdn.com/company/corporate-responsibility/sustainability",
        )

        # create our domains we use to look up each provider
        green_domain_factory.create(hosted_by=provider, url="www.hillbob.de")
        green_domain_factory.create(hosted_by=systen_upstream, url="sys-ten.com")
        green_domain_factory.create(hosted_by=cdn_upstream, url="cdn.com")

        psr = carbon_txt.CarbonTxtParser()
        result = psr.parse("www.hillbob.de", carbon_txt_string)

        org = result.get("org")
        assert org
        assert org.website == provider.website
        assert org.supporting_documents.first().url == sustainablity_page.url

        upstream_providers = result.get("upstream")

        assert upstream_providers

        # is our cdn provider upstream?
        parsed_cdn = [
            upstream for upstream in upstream_providers if upstream.name == "cdn.com"
        ][0]
        # is our hosting provider upstream?
        parsed_systen = [
            upstream
            for upstream in upstream_providers
            if upstream.name == "sys-ten.com"
        ][0]

        assert parsed_cdn.website == cdn_upstream.website
        assert (
            parsed_cdn.supporting_documents.first().url == cdn_sustainability_page.url
        )

        assert systen_upstream.website == parsed_systen.website
        assert (
            systen_upstream.supporting_documents.first().url
            == systen_sustainability_page.url
        )

    def test_parse_basic_provider_highlights_new_providers(
        self,
        db,
        carbon_txt_string,
        hosting_provider_factory,
        supporting_evidence_factory,
        green_domain_factory,
    ):
        """
        Where a provider isn't in the database we highlight it as a candidate for
        adding to the system
        """
        # create our main org hosting the carbon.txt file
        provider = hosting_provider_factory.create(
            name="www.hillbob.de", website="https://www.hillbob.de"
        )

        # create our upstream providers
        cdn_upstream = hosting_provider_factory.create(
            name="cdn.com", website="https://cdn.com"
        )
        supporting_evidence_factory.create(hostingprovider=cdn_upstream)

        # create our domains we use to look up each provider
        green_domain_factory.create(hosted_by=provider, url="www.hillbob.de")
        green_domain_factory.create(hosted_by=cdn_upstream, url="cdn.com")

        psr = carbon_txt.CarbonTxtParser()
        result = psr.parse("www.hillbob.de", carbon_txt_string)

        # is our system provider in our 'not registered' list?

        assert "not_registered" in result.keys()
        assert result["not_registered"]["providers"]
        unregistered_providers = result["not_registered"]["providers"]

        # is first member of providers in our 'not registered' list the
        # provider as listed in the carbon.txt file?
        assert len(unregistered_providers) == 1
        parsed_sys_ten, *rest = unregistered_providers
        assert parsed_sys_ten["domain"] == "sys-ten.com"
        assert (
            parsed_sys_ten["url"]
            == "https://www.sys-ten.de/en/about-us/our-data-centers/"
        )
        assert parsed_sys_ten["doctype"] == "sustainability-page"

    def test_parse_basic_provider_highlight_new_evidence(
        self,
        db,
        carbon_txt_string,
        hosting_provider_factory,
        supporting_evidence_factory,
        green_domain_factory,
    ):
        """
        Where there is supporting evidence we haven't seen before,
        we add it to the 'not_registered' part of the parse result

        """
        # Given: one provider to match our main provider in the carbon.txt file
        # with matching domain
        provider = hosting_provider_factory.create(
            name="www.hillbob.de", website="https://www.hillbob.de"
        )
        green_domain_factory.create(hosted_by=provider, url="www.hillbob.de")

        # Given: one upstream provider with a green domain to match
        # against in the carbon.txt file, but no pre-exisring evidence
        cdn_upstream = hosting_provider_factory.create(
            name="cdn.com", website="https://cdn.com"
        )
        green_domain_factory.create(hosted_by=cdn_upstream, url="cdn.com")

        # When we parse the carbon.txt file containing the evidence for the
        # cdn provider
        psr = carbon_txt.CarbonTxtParser()
        result = psr.parse("www.hillbob.de", carbon_txt_string)

        # Then: the evidence presented in the carbon.txt file
        # should show as not registered for the upstream cdn provider
        not_registered = result.get("not_registered")
        assert "evidence" in not_registered.keys()

        # and the evidence dictionary should have the properties defined
        # in the carbon.txt file
        cdn_evidence = [
            ev for ev in not_registered["evidence"] if ev["domain"] == "cdn.com"
        ]
        cdn_evidence_item, *rest = cdn_evidence

        assert cdn_evidence_item["domain"] == "cdn.com"
        assert cdn_evidence_item["doctype"] == "sustainability-page"
        assert (
            cdn_evidence_item["url"]
            == "https://cdn.com/company/corporate-responsibility/sustainability"
        )

    def test_check_after_parsing_provider_txt_file(self, db, carbon_txt_string):
        """
        Does a check against the domain return a positive result?
        """
        psr = carbon_txt.CarbonTxtParser()
        psr.parse_and_import("www.hillbob.de", carbon_txt_string)

        # now check for the domains
        res = gc_models.GreenDomain.check_for_domain("www.hillbob.de")
        provider = ac_models.Hostingprovider.objects.get(id=res.hosted_by_id)

        # do we have a green result?
        assert res.green is True
        assert res.hosted_by_id == provider.id

    def test_check_with_alternative_domain(self, db, carbon_txt_string):
        """
        Does a check against the domain return a positive result?
        """
        psr = carbon_txt.CarbonTxtParser()
        psr.parse_and_import("www.hillbob.de", carbon_txt_string)

        # now check for the domains
        res = gc_models.GreenDomain.check_for_domain("valleytrek.co.uk")
        provider = ac_models.Hostingprovider.objects.get(id=res.hosted_by_id)

        # do we have a green result?
        assert res.green is True
        assert res.hosted_by_id == provider.id

    def test_import_from_remote_carbon_text_file(self, db):
        psr = carbon_txt.CarbonTxtParser()
        result = psr.import_from_url("https://www.bergfreunde.de/carbon.txt")
        providers = ac_models.Hostingprovider.objects.all()
        assert len(providers) == 16
        assert len(result["upstream"]["providers"]) == 2
        assert len(result["org"]["providers"]) == 14

    def test_check_with_domain_aliases(self, db, carbon_txt_string):
        """
        Does
        """
        psr = carbon_txt.CarbonTxtParser()
        psr.parse_and_import("www.hillbob.de", carbon_txt_string)

        # now check for the domains
        primary_check = gc_models.GreenDomain.check_for_domain("www.hillbob.de")
        secondary_check = gc_models.GreenDomain.check_for_domain("valleytrek.co.uk")
        assert primary_check.green is True
        assert secondary_check.green is True

        # and the aliases
        for domain_alias in ["www.sys-ten.com", "www.systen.com"]:
            check = gc_models.GreenDomain.check_for_domain(domain_alias)
            assert check.green is True

        for domain_alias in ["hill-bob.ch", "www.hilbob.ch", "www.hill-bob.ch"]:
            check = gc_models.GreenDomain.check_for_domain(domain_alias)
            assert check.green is True

    @pytest.mark.skip(reason="pending")
    def test_creation_of_corporate_grouping(self):
        """
        Does parsing create the necessary corporate grouping from a
        carbon.txt file?
        """
        pass

    @pytest.mark.skip(reason="pending")
    def test_referencing_corporate_grouping(self):
        """
        After parsing a carbon.txt file, can checking an alternative domain
        refer to the correct corporate grouping too?
        """
        pass

    @pytest.mark.parametrize(
        "text_string", ("carbon_txt_string", "shorter_carbon_txt_string")
    )
    def test_parse_and_preview_carbon_text_file(
        self, db, carbon_txt_string, request, text_string
    ):
        # you can not parametrize fixtures, you need to fetch the value this way.
        # More below
        # https://doc.pytest.org/en/latest/reference/reference.html#pytest.FixtureRequest.getfixturevalue # noqa
        fixture_val = request.getfixturevalue(text_string)

        psr = carbon_txt.CarbonTxtParser()
        psr.parse_and_import("www.hillbob.de", carbon_txt_string)

        # we want to check that both forms work - the short and long versions
        parsed_result = psr.parse_and_preview("www.hillbob.de", fixture_val)

        sys_ten = gc_models.GreenDomain.objects.get(url="sys-ten.com").hosting_provider
        cdn_com = gc_models.GreenDomain.objects.get(url="cdn.com").hosting_provider
        hillbob = gc_models.GreenDomain.objects.get(
            url="www.hillbob.de"
        ).hosting_provider

        assert sys_ten in parsed_result["upstream"]["providers"]
        assert cdn_com in parsed_result["upstream"]["providers"]
        assert parsed_result["org"] == hillbob


class TestLogCarbonTxtCheck:
    """Check that a sitecheck registered by Carbontxt will load"""

    def test_log_sitecheck_to_database(
        self, db, carbon_txt_string, mocker, site_check_factory
    ):
        """
        Can we log a check that relies on a match with carbon.txt?
        """
        psr = carbon_txt.CarbonTxtParser()
        psr.parse_and_import("www.hillbob.de", carbon_txt_string)
        hillbob_de = Hostingprovider.objects.get(name="www.hillbob.de")
        dummy_check = site_check_factory.create(
            url="www.hillbob.de",
            ip=None,
            hosting_provider_id=hillbob_de.id,
            # we use WHOIS here, until we can use the correct ENUM
            # for mariadb in a migration
            match_type=choices.GreenlistChoice.WHOIS,
        )

        check_logger = workers.SiteCheckLogger()
        # we need to mock the lookup here for domain checker

        # mock our request to avoid the network call
        mocker.patch(
            "apps.greencheck.domain_check.GreenDomainChecker.check_domain",
            return_value=dummy_check,
        )

        check_logger.log_sitecheck_for_domain("www.hilbob.de")

        assert gc_models.Greencheck.objects.count() == 1
        logged_check = gc_models.Greencheck.objects.first()

        assert logged_check.url == dummy_check.url
        assert logged_check.type == dummy_check.match_type
        assert logged_check.type == "whois"
