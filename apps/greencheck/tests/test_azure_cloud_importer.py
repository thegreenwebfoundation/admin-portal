import pytest
import pathlib
import ipaddress
import json
from io import StringIO

from django.core.management import call_command
from apps.greencheck.management.commands import update_azure_ip_ranges
from apps.accounts.models import Hostingprovider
from apps.greencheck.models import GreencheckIp
# from apps.greencheck.management.commands.update_azure_ip_ranges import GREEN_REGIONS


@pytest.fixture
def hosting_provider():

    # oregon, *rest = [region for region in GREEN_REGIONS if region[1] == "us-west-2"]
    name, region, host_id = ("Azure US West", "az-west-2", 123)
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
        website="http://azure.microsoft.com",
    )


@pytest.fixture
def azure_cloud_provider(hosting_provider):
    hosting_provider.save()
    return update_azure_ip_ranges.MicrosoftCloudProvider()


@pytest.fixture
def azure_json_ip_ranges():
    this_file = pathlib.Path(__file__)
    json_path = this_file.parent.parent.joinpath("fixtures", "ip_ranges.json")
    with open(json_path) as ipr:
        ip_ranges = json.loads(ipr.read())
        return ip_ranges


@pytest.mark.django_db
class TestAZURECLoudImporter:
    def test_fetch_ip(self, hosting_provider, azure_cloud_provider):
        """
        Do we fetch the data from Azure?
        """
        hosting_provider.save()
        res = azure_cloud_provider.retrieve()

        assert len(res.keys()) == 3 # TODO: Figure out what value this should be

    def pullout_green_regions(self, hosting_provider, azure_cloud_provider):
        res = azure_cloud_provider.retrieve()

        _, region, host_id = azure_cloud_provider.green_regions[0]

        iprs = azure_cloud_provider.pullout_green_regions(res, region)

        ip_ranges = azure_cloud_provider.ip_ranges_for_hoster(iprs)

        assert isinstance(ip_ranges[0], ipaddress.IPv4Network)

    def test_update_hoster(self, hosting_provider, azure_cloud_provider):

        res = azure_cloud_provider.retrieve()
        _, region, host_id = ("Azure US West", "az-west-2", 123)
        # _, region, host_id = azure_cloud_provider.green_regions[0]
        # iprs = azure_cloud_provider.pullout_green_regions(res, region) # We don't have this as we don't have regions
        ip_ranges = azure_cloud_provider.convert_to_networks(res)

        ip_start, ip_end = ip_ranges[0][0], ip_ranges[0][-1]
        assert GreencheckIp.objects.all().count() == 0

        hosting_provider.save()

        # create one new green IP range
        azure_cloud_provider.update_hoster(hosting_provider, ip_start, ip_end)

        assert GreencheckIp.objects.all().count() == 1

    def test_update_range(
        self, hosting_provider, azure_cloud_provider, azure_json_ip_ranges
    ):
        assert GreencheckIp.objects.all().count() == 0
        hosting_provider.save()

        res, *rest = azure_cloud_provider.update_ranges(azure_json_ip_ranges)
        ipv4s = res["ipv4"]
        # ipv6s = res["ipv6"]
        assert len(ipv4s) == 104
        # assert len(ipv6s) == 20
        # we should have 124 ranges in total
        # assert GreencheckIp.objects.all().count() == len(ipv4s) + len(ipv6s)
        assert GreencheckIp.objects.all().count() == len(ipv4s)


@pytest.mark.django_db
class TestAZUREImportCommand:
    """
    This just tests that we have a management command that can run.
    We _could_ mock the call to fetch ip ranges, if this turns out to be a slow test.
    """

    def test_handle(self, azure_cloud_provider):
        out = StringIO()
        call_command("update_azure_ip_ranges", stdout=out)
        assert "Import Complete:" in out.getvalue()
