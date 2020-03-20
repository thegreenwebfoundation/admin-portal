import pytest

from apps.greencheck.management.commands import update_aws_ip_ranges
from apps.accounts.models import Hostingprovider

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
    return update_aws_ip_ranges.AmazonCloudProvider((
        ('Amazon US West', 'us-west-2', hosting_provider.id),
    ))

class TestAWSCLoudImporter:

    @pytest.mark.django_db
    def test_fetch_ip(self, hosting_provider, aws_cloud_provider):
        """
        Do we fetch the data from AWS?
        """
        hosting_provider.save()
        res = aws_cloud_provider.fetch_ip_ranges()

        assert(len(res.keys()) == 4 )

    
