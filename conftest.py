import pytest

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
    return update_aws_ip_ranges.AmazonCloudProvider((
        ('Amazon US West', 'us-west-2', hosting_provider.id),
    ))
