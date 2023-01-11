from ipaddress import ip_address
import pathlib

import pytest
import dramatiq
from django.contrib.auth import get_user_model

from django.contrib.auth import models as auth_models

from apps.accounts.models import (
    Hostingprovider,
    Datacenter,
    ProviderRequest,
    ProviderRequestStatus,
    ProviderRequestLocation,
)
from apps.greencheck.models import GreencheckIp, GreencheckASN

# from apps.greencheck.management.commands import update_aws_ip_ranges

from apps.greencheck.factories import UserFactory, SiteCheckFactory

from pytest_factoryboy import register
from apps.greencheck import factories as gc_factories

User = get_user_model()

register(gc_factories.UserFactory)
register(gc_factories.SiteCheckFactory)
register(gc_factories.TagFactory)
register(gc_factories.GreencheckFactory)
register(gc_factories.HostingProviderFactory)
register(gc_factories.GreenIpFactory)
register(gc_factories.GreenDomainFactory)
register(gc_factories.DailyStatFactory)
register(gc_factories.SiteCheckFactory)


@pytest.fixture
def provider_groups():
    return auth_models.Group.objects.filter(name__in=["datacenter", "hostingprovider"])


@pytest.fixture
def sample_hoster_user(provider_groups):
    """A user created when they register"""
    user = UserFactory.build(username="joebloggs", email="joe@example.com")
    user.set_password("topSekrit")
    user.save()

    user.groups.add(*provider_groups)
    [grp.save() for grp in provider_groups]
    user.save()

    return user


@pytest.fixture
def greenweb_staff_user():
    """
    Create a user with the permissions and group ownership
    of internal green web staff, who are paid to maintain
    the database
    """
    user = UserFactory.build(username="greenweb_staff", email="staff@greenweb.org")
    user.set_password("topSekrit")

    # give them an id so we can set up many to many relationships with groups
    user.save()

    groups = auth_models.Group.objects.filter(
        name__in=["admin", "datacenter", "hostingprovider"]
    )

    user.groups.add(*groups)
    [grp.save() for grp in groups]
    user.save()
    return user


@pytest.fixture
def sample_sitecheck():
    return SiteCheckFactory.build()


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
def csv_file():
    this_file = pathlib.Path(__file__)
    return this_file.parent.joinpath(
        "apps", "greencheck", "fixtures", "test_dataset_conftest.csv"
    )


# test broker, so we don't need to rely on rabbit for tests
@pytest.fixture
def broker():
    broker = dramatiq.get_broker()
    broker.flush_all()
    return broker


@pytest.fixture
def worker(broker):
    worker = dramatiq.Worker(broker, worker_timeout=100)
    worker.start()
    yield worker
    worker.stop()
