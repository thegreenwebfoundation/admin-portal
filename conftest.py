import pathlib

import pytest
import dramatiq
from apps.greencheck.legacy_workers import SiteCheck
from django.contrib.auth import get_user_model

from django.contrib.auth import models as auth_models

from apps.accounts.models import Hostingprovider, Datacenter
from apps.greencheck.models import GreencheckIp, GreencheckASN
from apps.greencheck.management.commands import update_aws_ip_ranges

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


@pytest.fixture
def sample_hoster_user(default_user_groups):
    u = UserFactory.build(username="joebloggs", email="joe@example.com")
    u.set_password("topSekrit")
    admin, hostingprovider = default_user_groups
    u.save()
    u.groups.add(hostingprovider)

    return u


@pytest.fixture
def sample_user(default_user_groups):
    u = UserFactory.build(username="joebloggs", email="joe@example.com")
    u.set_password("topSekrit")
    admin, hostingprovider = default_user_groups
    u.save()

    return u


@pytest.fixture
def default_user_groups():
    """
    Set up the different groups we assume a user can
    be part of as an external user.
    """
    admin, admin_created = auth_models.Group.objects.get_or_create(name="admin")
    hostingprovider, hp_created = auth_models.Group.objects.get_or_create(
        name="hostingprovider"
    )
    hp_perm_codenames = [
        "add_datacenter",
        "change_datacenter",
        "view_datacenter",
        "add_datacentercertificate",
        "change_datacentercertificate",
        "delete_datacentercertificate",
        "view_datacentercertificate",
        "add_datacenterclassification",
        "change_datacenterclassification",
        "delete_datacenterclassification",
        "view_datacenterclassification",
        "add_datacentercooling",
        "change_datacentercooling",
        "delete_datacentercooling",
        "view_datacentercooling",
        "add_datacentresupportingdocument",
        "change_datacentresupportingdocument",
        "delete_datacentresupportingdocument",
        "view_datacentresupportingdocument",
        "add_hostingprovider",
        "change_hostingprovider",
        "view_hostingprovider",
        "add_hostingprovidercertificate",
        "change_hostingprovidercertificate",
        "delete_hostingprovidercertificate",
        "view_hostingprovidercertificate",
        "add_hostingproviderdatacenter",
        "change_hostingproviderdatacenter",
        "delete_hostingproviderdatacenter",
        "view_hostingproviderdatacenter",
        "add_hostingprovidersupportingdocument",
        "change_hostingprovidersupportingdocument",
        "delete_hostingprovidersupportingdocument",
        "view_hostingprovidersupportingdocument",
        "change_user",
        "view_user",
        "add_greencheckasn",
        "change_greencheckasn",
        "view_greencheckasn",
        "view_greencheckasnapprove",
        "add_greencheckip",
        "change_greencheckip",
        "view_greencheckip",
        "view_greencheckipapprove",
    ]

    hp_perms = [
        perm
        for perm in auth_models.Permission.objects.filter(
            codename__in=hp_perm_codenames
        )
    ]

    for perm in hp_perms:
        hostingprovider.permissions.add(perm)
    hostingprovider.save()

    admin_perm_codenames = []

    # TODO: see the idiomatic way to track these perms and groups in django
    # we currently check for group membership, _not_ permissions, and we
    # likely should
    admin_perms = [
        perm
        for perm in auth_models.Permission.objects.filter(
            codename__in=admin_perm_codenames
        )
    ]

    for perm in admin_perms:
        admin.permissions.add(perm)
    hostingprovider.save()

    return [admin, hostingprovider]


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
    return GreencheckASN(active=True, asn=12345, hostingprovider=hosting_provider,)


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
