import pathlib

import dramatiq
import factory
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth import models as auth_models
from guardian.shortcuts import assign_perm
from pytest_factoryboy import register

from apps.accounts import factories as ac_factories
from apps.accounts import models as ac_models
from apps.accounts.permissions import manage_datacenter, manage_provider
from apps.greencheck import factories as gc_factories
from apps.greencheck.models import GreencheckASN, GreencheckIp

# https://factoryboy.readthedocs.io/en/stable/recipes.html#using-reproducible-randomness
factory.random.reseed_random("venture not into the land of flaky tests")

User = get_user_model()

register(gc_factories.UserFactory)
register(gc_factories.SiteCheckFactory)
register(gc_factories.GreencheckFactory)
register(gc_factories.ServiceFactory)
register(gc_factories.HostingProviderFactory)
register(gc_factories.GreenIpFactory)
register(gc_factories.GreenASNFactory)
register(gc_factories.GreenDomainFactory)
register(gc_factories.SiteCheckFactory)
register(ac_factories.SupportingEvidenceFactory)
register(ac_factories.ProviderRequestFactory)


@pytest.fixture
def provider_groups():
    return auth_models.Group.objects.filter(name__in=["datacenter", "hostingprovider"])


@pytest.fixture
def sample_hoster_user(provider_groups):
    """A user created when they register"""
    user = gc_factories.UserFactory.build(username="joebloggs", email="joe@example.com")
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
    user = gc_factories.UserFactory.build(
        username="greenweb_staff", email="staff@greenweb.org"
    )
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
    return gc_factories.SiteCheckFactory.build()


@pytest.fixture
def hosting_provider():
    return ac_models.Hostingprovider(
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
def user_with_provider(sample_hoster_user):
    """
    Return a user that's been persisted to the database,
    and has a hosting provider associated with it
    """
    hp = gc_factories.HostingProviderFactory.create(created_by=sample_hoster_user)
    assign_perm(manage_provider.codename, sample_hoster_user, hp)
    return sample_hoster_user


@pytest.fixture
def hosting_provider_with_sample_user(hosting_provider, sample_hoster_user):
    """
    Return a hosting provider that's been persisted to the database,
    and has a user associated with it
    """
    hosting_provider.created_by = sample_hoster_user
    hosting_provider.save()
    assign_perm(manage_provider.codename, sample_hoster_user, hosting_provider)
    return hosting_provider


@pytest.fixture
def datacenter(sample_hoster_user):
    dc = ac_models.Datacenter(
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
        created_by=sample_hoster_user,
        virtual=False,
        website="http://www.xs4all.nl/zakelijk/colocation/datacenters/dc2.php",
    )
    dc.save()
    assign_perm(manage_datacenter.codename, sample_hoster_user, dc)
    return dc


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
