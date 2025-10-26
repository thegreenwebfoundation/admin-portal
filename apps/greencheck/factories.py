import datetime
import ipaddress
import random

import factory
import factory.django as dj_factory
import factory.fuzzy as facfuzzy
from django.contrib.auth import get_user_model
from django.db.models import signals
from django.utils import timezone

from apps.accounts import models as ac_models
from apps.accounts.models import choices as ac_choices
from apps.greencheck.models.checks import GreenDomain

from . import models as gc_models


# https://factoryboy.readthedocs.io/en/stable/recipes.html#using-reproducible-randomness
factory.random.reseed_random("venture not into the land of flaky tests")


class UserFactory(dj_factory.DjangoModelFactory):
    username = factory.Faker("user_name")
    email = factory.Faker("email")
    password = factory.Faker("password")

    class Meta:
        model = get_user_model()
        django_get_or_create = ["username"]


class SiteCheckFactory(factory.Factory):
    url = factory.Faker("domain_name")
    ip = factory.Faker("ipv4")
    data = False
    green = False
    hosting_provider_id = 595
    checked_at = facfuzzy.FuzzyDateTime(
        datetime.datetime(2009, 1, 1, tzinfo=datetime.timezone.utc)
    )
    match_type = None
    match_ip_range = None
    cached = False

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        # Until we use a different database we need datetimes to not
        # be timezone aware. This strips timeonze from the fuzzy datetime
        # https://factoryboy.readthedocs.io/en/latest/reference.html#factory.Factory._adjust_kwargs
        kwargs["checked_at"] = timezone.make_naive(kwargs["checked_at"])
        return kwargs

    class Meta:
        model = gc_models.SiteCheck


class ServiceFactory(dj_factory.DjangoModelFactory):
    name = factory.Faker("word")

    class Meta:
        model = ac_models.Service
        # avoid creating duplicate entries
        django_get_or_create = ("name",)


class GreencheckFactory(dj_factory.DjangoModelFactory):
    hostingprovider = factory.Faker("random_int")
    greencheck_ip = factory.Faker("random_int")
    date = facfuzzy.FuzzyDateTime(datetime.datetime(2009, 1, 1, tzinfo=datetime.timezone.utc))
    green = "no"
    ip = factory.Faker("ipv4")
    tld = factory.Faker("tld")
    type = "None"
    url = factory.Faker("domain_name")

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        #
        if timezone.is_aware(kwargs["date"]):
            kwargs["date"] = timezone.make_naive(kwargs["date"])
        return kwargs

    class Meta:
        model = gc_models.Greencheck


class HostingProviderFactory(dj_factory.DjangoModelFactory):
    """
    Basic hosting provider, with no extra bits
    """

    archived = False
    # country = dj_countries.CountryField(db_column="countrydomain")
    country = "US"
    customer = False
    # icon = models.CharField(max_length=50, blank=True)
    # iconurl = models.CharField(max_length=255, blank=True)
    model = ac_choices.ModelType.COMPENSATION
    name = factory.Faker("company")
    created_by = factory.SubFactory(UserFactory)
    # partner = models.CharField(
    #     max_length=255,
    #     null=True,
    #     default=gc_choicesPartnerChoice.NONE,
    #     choices=gc_choices.PartnerChoice.choices,
    #     blank=True,
    # )
    # services = TaggableManager(
    #     verbose_name="Services Offered",
    #     help_text="Click the services that your organisation offers. These will be listed in the green web directory.",
    # )
    # is_listed = models.BooleanField(verbose_name="Show on website", default=False)
    website = factory.Faker("domain_name")
    # datacenter = models.ManyToManyField(
    #     "Datacenter",
    #     through="HostingproviderDatacenter",
    #     through_fields=("hostingprovider", "datacenter"),
    #     related_name="hostingproviders",
    # )

    @factory.post_generation
    def services(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.services.set(*extracted)

    class Meta:
        model = ac_models.Hostingprovider
        django_get_or_create = ("name",)


class GreenIpFactory(dj_factory.DjangoModelFactory):
    active = True
    ip_start = factory.Faker("ipv4_public")
    ip_end = factory.Faker("ipv4_public")
    hostingprovider = factory.SubFactory(HostingProviderFactory)

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        """
        We make sure IP start is lower than the ip_end,
        so we have a valid ip range
        """
        # parse the ips
        start_ip = ipaddress.ip_address(kwargs["ip_start"])
        end_ip = start_ip + random.randint(0, 20)
        kwargs["ip_end"] = str(end_ip)

        return kwargs

    class Meta:
        model = gc_models.GreencheckIp


class GreenASNFactory(dj_factory.DjangoModelFactory):
    active = True
    asn = factory.Faker("random_int")
    hostingprovider = factory.SubFactory(HostingProviderFactory)

    class Meta:
        model = gc_models.GreencheckASN


class GreenDomainFactory(dj_factory.DjangoModelFactory):
    url = factory.Faker("domain_name")
    green = True
    hosted_by = factory.SubFactory(HostingProviderFactory)
    listed_provider = factory.SelfAttribute("hosted_by.is_listed")
    # see the `_adjust_kwargs` step, for checking that
    # hosting provider info is realistic
    hosted_by_id = factory.SelfAttribute("hosted_by")
    hosted_by_website = factory.SelfAttribute("hosted_by")
    modified = timezone.now()

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        """
        Override the `hosted_by` property, based on
        the values we pull out from the hosting provider
        object. We need to do this, because we don't have a proper
        foreign key to hosting providers.
        """

        hosting_provider = kwargs["hosted_by"]
        kwargs["hosted_by"] = hosting_provider.name
        kwargs["hosted_by_id"] = hosting_provider.id
        kwargs["hosted_by_website"] = hosting_provider.website

        return kwargs

    class Meta:
        model = GreenDomain
        django_get_or_create = ("url",)


@factory.django.mute_signals(signals.pre_save)
class GreenDomainBadgeFactory(dj_factory.DjangoModelFactory):
    domain = factory.Faker("domain_name")
    path = factory.LazyAttribute(lambda b: f"greenweb_badges/{b.domain}.png")

    class Meta:
        model = gc_models.GreenDomainBadge
