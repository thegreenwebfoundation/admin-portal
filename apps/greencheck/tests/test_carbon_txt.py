import ipdb
import pytest
import pathlib
import rich

from .. import carbon_txt
from ...accounts import models as ac_models
from .. import models as gc_models


@pytest.fixture
def carbon_txt_string():
    pth = pathlib.Path(__file__)

    carbon_txt_path = pth.parent / "carbon-txt-test.toml"

    carbon_txt_string = None
    with open(carbon_txt_path) as carb_file:
        carbon_txt_string = carb_file.read()

    return carbon_txt_string


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

    @pytest.mark.only
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
        assert res.green == True
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
        assert res.green == True
        assert res.hosted_by_id == provider.id

    def test_import_from_remote_carbon_text_file(self, db):
        psr = carbon_txt.CarbonTxtParser()
        result = psr.import_from_url("https://www.bergfreunde.de/carbon.txt")
        providers = ac_models.Hostingprovider.objects.all()
        assert len(providers) == 16
        assert len(result["upstream"]["providers"]) == 2
        assert len(result["org"]["providers"]) == 14

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
