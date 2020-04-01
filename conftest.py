import pathlib

import pytest

from apps.accounts.models import Hostingprovider
from apps.greencheck.models import GreencheckIp
from apps.accounts.models import User


@pytest.fixture
def hosting_user(hosting_provider):

    hosting_provider.save()

    user = User(
        username='joe_bloggs',
        email='joe.bloggs@greening.digital',
        # for tests to pass, we NEED a hosting provider
        # this can't be right.
        hostingprovider=hosting_provider
    )
    user.save()

    return user


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
