import logging
import pytest
import io
from django.core import management

from ....accounts import models as ac_models


logger = logging.getLogger(__name__)
console = logging.StreamHandler()
# logger.setLevel(logging.DEBUG)
# logger.addHandler(console)

FIRST_OF_JAN = "2020-01-01"


class TestImportFromCarbonTxt:
    @pytest.mark.only
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

