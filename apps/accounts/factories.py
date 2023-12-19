from django.utils import timezone
from dateutil.relativedelta import relativedelta
import factory
import factory.django as dj_factory
from ipaddress import ip_address
from apps.accounts import models as ac_models

from apps.greencheck import factories as gc_factories

# https://factoryboy.readthedocs.io/en/stable/recipes.html#using-reproducible-randomness
factory.random.reseed_random("venture not into the land of flaky tests")


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


# class ProviderRequestFactory(dj_factory.DjangoModelFactory):
#     """
#     A provider request as if it had been created by a user going through
#     our form wizard
#     """

#     name = factory.Faker("sentence")
#     website = factory.Faker("url")
#     description = factory.Faker("sentence", nb=10)
#     status = factory.Faker(
#         "random_element", elements=ac_models.ProviderRequestStatus.choices
#     )

#     # created_by = models.ForeignKey(
#     #     settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True
#     # )
#     # authorised_by_org = models.BooleanField()
#     # services = TaggableManager(
#     #     verbose_name="Services offered",
#     #     help_text=(
#     #         "Click the services that your organisation offers. These will be listed in"
#     #         " the green web directory."
#     #     ),
#     #     blank=True,
#     #     through=ProviderRequestService,
#     # )
#     @factory.post_generation
#     def services(self, create, extracted, **kwargs):
#         if not create:
#             return

#         if extracted:
#             self.services.set(*extracted)

#     # missing_network_explanation = models.TextField(
#     #     verbose_name="Reason for no IP / AS data",
#     #     help_text=(
#     #         "If an organisation is not listing IP Ranges and AS numbers, "
#     #         "we need a way to identify them in network lookups."
#     #     ),
#     #     blank=True,
#     # )
#     # location_import_required = models.BooleanField(default=False)
#     # network_import_required = models.BooleanField(default=False)
#     # data_processing_opt_in = models.BooleanField(
#     #     default=False, verbose_name="Data processing consent"
#     # )
#     # newsletter_opt_in = models.BooleanField(
#     #     default=False, verbose_name="Newsletter signup"
#     # )
#     # # if this field is set, approving a request will update the provider instead of creating a new one
#     # provider = models.ForeignKey(
#     #     to=Hostingprovider, on_delete=models.SET_NULL, null=True
#     # )

#     class Meta:
#         model = ac_models.ProviderRequest


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
