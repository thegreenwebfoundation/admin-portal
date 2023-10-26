import io
import logging

import pytest
from django.core import management

from ....accounts import models as ac_models
from ... import domain_check

logger = logging.getLogger(__name__)


class TestImportFromCarbonTxt:
    # @pytest.mark.only
    def test_import_from_url(self, db):
        """
        Check we can run an import from the command line
        """
        out = io.StringIO()
        management.call_command(
            "import_from_carbon_txt_url",
            "https://www.bergfreunde.it/carbon.txt",
            stdout=out,
        )

        providers = ac_models.Hostingprovider.objects.all()
        assert len(providers) == 16
        assert "OK" in out.getvalue()

        # do we name the providers we have imported?
        names = [prov.name for prov in providers]
        for name in names:
            assert name in out.getvalue()

    # @pytest.mark.only
    def test_import_from_url_then_check_against_api(self, db, client):
        """
        Sanity check to make sure we don't override the imported
        information with our async lookup process.
        """
        out = io.StringIO()
        url = "bergfreunde.it"

        # run an import
        management.call_command(
            "import_from_carbon_txt_url",
            "https://www.bergfreunde.it/carbon.txt",
            stdout=out,
        )

        checker = domain_check.GreenDomainChecker()
        sitecheck = checker.check_domain(url)

        # we use the sitecheck status to keep the GreenDomain
        # table up to date, and our async workers update the status
        # in the Greendomain table after each check.
        # Checking the status here saves us needing to have all
        # the async checking infra with workers, and brokers in our
        # test
        assert sitecheck.green
