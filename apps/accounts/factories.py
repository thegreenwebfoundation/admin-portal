from django.utils import timezone
from dateutil.relativedelta import relativedelta
import factory
import factory.django as dj_factory

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
