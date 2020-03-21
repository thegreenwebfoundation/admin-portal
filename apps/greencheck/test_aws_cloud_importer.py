import pytest
import pathlib
import ipaddress
import json

from apps.greencheck.management.commands import update_aws_ip_ranges
from apps.accounts.models import Hostingprovider
from apps.greencheck.models import GreencheckIp

@pytest.fixture
def hosting_provider():

    return Hostingprovider(
        archived= False,
        country= 'US',
        customer= False,
        icon= '',
        iconurl= '',
        model= 'groeneenergie',
        name= 'Amazon US West',
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


class TestAWSCLoudImporter:

    @pytest.mark.django_db
    def test_fetch_ip(self, hosting_provider, aws_cloud_provider):
        """
        Do we fetch the data from AWS?
        """
        hosting_provider.save()
        res = aws_cloud_provider.fetch_ip_ranges()

        assert(len(res.keys()) == 4 )


    @pytest.mark.django_db
    def pullout_green_regions(self, hosting_provider, aws_cloud_provider):
        res = aws_cloud_provider.fetch_ip_ranges()

        _, region, host_id = aws_cloud_provider.green_regions[0]

        iprs = aws_cloud_provider.pullout_green_regions(res, region)

        ip_ranges = aws_cloud_provider.ip_ranges_for_hoster(iprs)

        assert(isinstance(ip_ranges[0], ipaddress.IPv4Network))

    @pytest.mark.django_db
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

    @pytest.mark.django_db
    def test_range(self, hosting_provider, aws_cloud_provider, aws_json_ip_ranges):
        assert(GreencheckIp.objects.all().count() == 0)
        hosting_provider.save()

        res = aws_cloud_provider.update_ranges(aws_cloud_provider.fetch_ip_ranges())
        ipv4s = res['ipv4']
        ipv6s = res['ipv6']


        assert(len(ipv4s) == 104)
        assert(len(ipv6s) == 20)
        # we should have 124 ranges in total
        assert(GreencheckIp.objects.all().count() == len(ipv4s) + len(ipv6s))
