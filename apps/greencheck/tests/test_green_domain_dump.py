import pytest
import pathlib

from io import StringIO

from django.core.management import call_command
from apps.greencheck.management.commands import dump_green_domains
from apps.accounts.models import Hostingprovider
from apps.greencheck.models import GreencheckIp


@pytest.fixture
def hosting_provider():

    oregon, *rest = [region for region in GREEN_REGIONS if region[1] == "us-west-2"]
    name, region, host_id = oregon
    return Hostingprovider(
        archived=False,
        country="US",
        customer=False,
        icon="",
        iconurl="",
        id=host_id,
        model="groeneenergie",
        name=name,
        partner="",
        showonwebsite=True,
        website="http://aws.amazon.com",
    )


@pytest.mark.django_db
class TestGreenDomainExporter:
    def test_dump_green_domains(self,):
        """
        """
        # set up


@pytest.mark.django_db
class TestDumpGreenDomainCommand:
    """

    """

    def test_handle(self):
        out = StringIO()
        call_command("dump_green_domains", stdout=out)
        assert "Import Complete:" in out.getvalue()
