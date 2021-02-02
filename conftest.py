import pathlib

import pytest

from apps.accounts.models import Hostingprovider, Datacenter
from apps.greencheck.models import GreencheckIp
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def sample_hoster_user():
    u = User(username="joebloggs", email="joe@example.com")
    u.set_password("topSekrit")
    return u

@pytest.fixture
def hosting_provider():

    return Hostingprovider(
        archived=False,
        country="US",
        customer=False,
        icon="",
        iconurl="",
        model="groeneenergie",
        name="Amazon US West",
        partner="",
        showonwebsite=True,
        website="http://aws.amazon.com",
    )

@pytest.fixture
def datacenter():

    return Datacenter(
        country= 'NL',
        dc12v=False,
        greengrid=True,
        mja3=True,
        model='groeneenergie',
        name='KPN DC2',
        pue=1.3,
        residualheat=False,
        showonwebsite=True,
        temperature=22,
        temperature_type='C',
        user_id=None,
        virtual=False,
        website='http://www.xs4all.nl/zakelijk/colocation/datacenters/dc2.php'
    )


@pytest.fixture
def green_ip(hosting_provider):
    hosting_provider.save()
    return GreencheckIp.objects.create(
        active=True,
        ip_start="172.217.168.238",
        ip_end="172.217.168.239",
        hostingprovider=hosting_provider,
    )


@pytest.fixture
def aws_cloud_provider(hosting_provider):
    return update_aws_ip_ranges.AmazonCloudProvider(
        (("Amazon US West", "us-west-2", hosting_provider.id),)
    )


@pytest.fixture
def csv_file():
    this_file = pathlib.Path(__file__)
    return this_file.parent.joinpath(
        "apps", "greencheck", "fixtures", "import_data.csv"
    )
