import pytest
import pathlib

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

@pytest.fixture
def csv_file():
    this_file = pathlib.Path(__file__)
    return this_file.parent.joinpath("apps","greencheck", "fixtures", "import_data.csv")