import pathlib
import pytest
import dramatiq
import factory

import apps.accounts.models as ac_models

from django.contrib.auth import get_user_model
from django.contrib.auth import models as auth_models
from pytest_factoryboy import register
from ipaddress import ip_address

from apps.greencheck.models import GreencheckIp, GreencheckASN
from apps.greencheck import factories as gc_factories
from apps.accounts import factories as ac_factories


# https://factoryboy.readthedocs.io/en/stable/recipes.html#using-reproducible-randomness
factory.random.reseed_random("venture not into the land of flaky tests")

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

register(ac_factories.SupportingEvidenceFactory)


class ProviderRequestFactory(factory.django.DjangoModelFactory):
    """
    By default ProviderRequestFactory() or ProviderRequestFactory.create()
    will return an object with no services. This is because of
    how factory-boy manages many-to-many relationships.

    Services can be set in the following ways:
    - pr = ProviderRequestFactory(); pr.services.set(["service1", "service2"])
    - ProviderRequestFactory.create(services=["service1", "service2"])
    """

    name = factory.Faker("word")
    website = factory.Faker("domain_name")
    description = factory.Faker("sentence")
    status = ac_models.ProviderRequestStatus.OPEN
    created_by = factory.SubFactory(gc_factories.UserFactory)
    authorised_by_org = True

    class Meta:
        model = ac_models.ProviderRequest

    @factory.post_generation
    def services(self, create, extracted, **kwargs):
        """
        This handles many-to-many relationship between ProviderRequest and Tag.

        More details: https://factoryboy.readthedocs.io/en/latest/recipes.html#simple-many-to-many-relationship
        """  # noqa
        # nothing passed as an argument
        if not create or not extracted:
            return
        # set tags
        for tag in extracted:
            self.services.add(tag)


class ProviderRequestLocationFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("word")
    city = factory.Faker("city")
    country = factory.Faker("country_code")
    request = factory.SubFactory(ProviderRequestFactory)

    class Meta:
        model = ac_models.ProviderRequestLocation


class ProviderRequestEvidenceFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("sentence", nb_words=6)
    link = factory.Faker("url")
    file = None
    type = factory.Faker("random_element", elements=ac_models.EvidenceType.values)
    public = factory.Faker("random_element", elements=[True, False])
    request = factory.SubFactory(ProviderRequestFactory)

    class Meta:
        model = ac_models.ProviderRequestEvidence


class ProviderRequestIPRangeFactory(factory.django.DjangoModelFactory):
    start = factory.Faker("ipv4")
    end = factory.LazyAttribute(lambda o: str(ip_address(o.start) + 10))
    request = factory.SubFactory(ProviderRequestFactory)

    class Meta:
        model = ac_models.ProviderRequestIPRange


class ProviderRequestASNFactory(factory.django.DjangoModelFactory):
    asn = factory.Faker("random_int")
    request = factory.SubFactory(ProviderRequestFactory)

    class Meta:
        model = ac_models.ProviderRequestASN


class ProviderRequestConsentFactory(factory.django.DjangoModelFactory):
    data_processing_opt_in = True
    newsletter_opt_in = factory.Faker("random_element", elements=[True, False])
    request = factory.SubFactory(ProviderRequestFactory)

    class Meta:
        model = ac_models.ProviderRequestConsent


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
    hp = gc_factories.HostingProviderFactory.create()
    sample_hoster_user.hostingprovider = hp
    sample_hoster_user.save()
    return sample_hoster_user


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
    return ac_models.Datacenter(
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
