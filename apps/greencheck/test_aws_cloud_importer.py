import pytest
import pathlib
import ipaddress
import json
from io import StringIO

from django.core.management import call_command
from apps.greencheck.management.commands import update_aws_ip_ranges
from apps.accounts.models import Hostingprovider
from apps.greencheck.models import GreencheckIp
from apps.greencheck.management.commands.update_aws_ip_ranges import GREEN_REGIONS


@pytest.fixture
def hosting_provider():

    oregon, *rest = [
        region for region in GREEN_REGIONS
        if region[1] == "us-west-2"
    ]
    name, region, host_id = oregon
    return Hostingprovider(
        archived= False,
        country= 'US',
        customer= False,
        icon= '',
        iconurl= '',
        id = host_id,
        model= 'groeneenergie',
        name= name,
        partner= '',
        showonwebsite= True,
        website= 'http://aws.amazon.com'
    )

@pytest.fixture
def aws_cloud_provider(hosting_provider):
    hosting_provider.save()
    return update_aws_ip_ranges.AmazonCloudProvider(green_regions=(
        ('Amazon US West', 'us-west-2', hosting_provider.id),
    ))

@pytest.fixture
def aws_json_ip_ranges():
    this_file = pathlib.Path(__file__)
    json_path = this_file.parent.joinpath('fixtures', "ip_ranges.json")
    with open(json_path) as ipr:
        ip_ranges = json.loads(ipr.read())
        return ip_ranges


@pytest.mark.django_db
class TestAWSCLoudImporter:

    def test_fetch_ip(self, hosting_provider, aws_cloud_provider):
        """
        Do we fetch the data from AWS?
        """
        hosting_provider.save()
        res = aws_cloud_provider.fetch_ip_ranges()

        assert(len(res.keys()) == 4 )

    def pullout_green_regions(self, hosting_provider, aws_cloud_provider):
        res = aws_cloud_provider.fetch_ip_ranges()

        _, region, host_id = aws_cloud_provider.green_regions[0]

        iprs = aws_cloud_provider.pullout_green_regions(res, region)

        ip_ranges = aws_cloud_provider.ip_ranges_for_hoster(iprs)

        assert(isinstance(ip_ranges[0], ipaddress.IPv4Network))

    def test_update_hoster(self, hosting_provider, aws_cloud_provider):

        res = aws_cloud_provider.fetch_ip_ranges()
        _, region, host_id = aws_cloud_provider.green_regions[0]
        iprs = aws_cloud_provider.pullout_green_regions(res, region)
        ip_ranges = aws_cloud_provider.ip_ranges_for_hoster(iprs)

        ip_start, ip_end = ip_ranges[0][0], ip_ranges[0][-1]
        assert(GreencheckIp.objects.all().count() == 0)

        hosting_provider.save()

        # create one new green IP range
        aws_cloud_provider.update_hoster(hosting_provider, ip_start, ip_end)

        assert(GreencheckIp.objects.all().count() == 1)

    def test_update_range(self, hosting_provider, aws_cloud_provider, aws_json_ip_ranges):
        assert(GreencheckIp.objects.all().count() == 0)
        hosting_provider.save()

        res, *rest = aws_cloud_provider.update_ranges(aws_cloud_provider.fetch_ip_ranges())
        ipv4s = res['ipv4']
        ipv6s = res['ipv6']


        assert(len(ipv4s) == 104)
        assert(len(ipv6s) == 20)
        # we should have 124 ranges in total
        assert(GreencheckIp.objects.all().count() == len(ipv4s) + len(ipv6s))


@pytest.mark.django_db
class TestAWSImportCommand:

    def test_handle(self, aws_cloud_provider):
        out = StringIO()
        call_command('update_aws_ip_ranges', stdout=out)
        assert('Import Complete:' in out.getvalue())

