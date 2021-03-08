import pathlib

import pytest

from apps.greencheck.legacy_workers import SiteCheck
from django.contrib.auth import get_user_model

from apps.accounts.models import Hostingprovider, Datacenter
from apps.greencheck.models import GreencheckIp, GreencheckASN
from apps.greencheck.management.commands import update_aws_ip_ranges

User = get_user_model()


@pytest.fixture
def sample_hoster_user():
    u = User(username="joebloggs", email="joe@example.com")
    u.set_password("topSekrit")
    return u


@pytest.fixture
def sample_sitecheck():

    return SiteCheck(
        url="somesite.berlin",
        ip="192.30.252.153",
        data=True,
        green=True,
        hosting_provider_id=595,
        checked_at="2021-01-20 13:35:52",
        match_type=None,
        match_ip_range=None,
        cached=True,
    )


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
def hosting_provider_aws():

    oregon, *rest = [
        region
        for region in update_aws_ip_ranges.GREEN_REGIONS
        if region[1] == "us-west-2"
    ]
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


@pytest.fixture
def hosting_provider_with_sample_user(hosting_provider, sample_hoster_user):
    """
    Return a hosting provider that's been persisted to the database,
    and has a user associated with it
    """
    hosting_provider.save()
    sample_hoster_user.hostingprovider = hosting_provider
    sample_hoster_user.save()
    return hosting_provider


@pytest.fixture
def datacenter():

    return Datacenter(
        country="NL",
        dc12v=False,
        greengrid=True,
        mja3=True,
        model="groeneenergie",
        name="KPN DC2",
        pue=1.3,
        residualheat=False,
        showonwebsite=True,
        temperature=22,
        temperature_type="C",
        user_id=None,
        virtual=False,
        website="http://www.xs4all.nl/zakelijk/colocation/datacenters/dc2.php",
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
def green_asn(hosting_provider):
    hosting_provider.save()
    return GreencheckASN(
        active=True,
        asn=12345,
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
