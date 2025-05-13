from ipaddress import ip_address

import factory
import factory.django as dj_factory
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from apps.accounts import models as ac_models
from apps.greencheck import factories as gc_factories

# https://factoryboy.readthedocs.io/en/stable/recipes.html#using-reproducible-randomness
factory.random.reseed_random("venture not into the land of flaky tests")


class VerificationBasisFactory(dj_factory.DjangoModelFactory):
    name = factory.Faker("word")

    class Meta:
        model = ac_models.VerificationBasis
        # avoid creating duplicate entries
        django_get_or_create = ("name",)


class SupportingEvidenceFactory(dj_factory.DjangoModelFactory):
    """
    A piece of supporting evidence, at a remote url, rather than uploaded
    """

    title = factory.Faker("sentence")
    description = factory.Faker("sentence")
    type = factory.Faker("random_element", elements=ac_models.EvidenceType.values)
    url = factory.Faker("url")
    public = factory.Faker("random_element", elements=[True, False])
    hostingprovider = factory.SubFactory(gc_factories.HostingProviderFactory)
    valid_from = timezone.now()
    valid_to = timezone.now() + relativedelta(years=1)

    class Meta:
        model = ac_models.HostingProviderSupportingDocument


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

    @factory.post_generation
    def verification_bases(self, create, extracted, **kwargs):
        """
        This handles many-to-many relationship between ProviderRequest and VerificationBasis.

        More details: https://factoryboy.readthedocs.io/en/latest/recipes.html#simple-many-to-many-relationship
        """  # noqa
        # nothing passed as an argument
        if not create or not extracted:
            return
        # set tags
        for tag in extracted:
            self.verification_bases.add(tag)

    class Meta:
        model = ac_models.ProviderRequest


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
