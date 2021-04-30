from typing import Any, Sequence

import factory
import factory.fuzzy as facfuzzy
import factory.django as dj_factory

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models.signals import post_save
from django.db import models
from django.utils import timezone

from django_countries import fields as dj_countries


# RelatedFactory,
# SubFactory,
# post_generation,


from taggit.models import Tag
from . import models as gc_models
from . import choices as gc_choices

from apps.accounts import models as ac_models
from apps.accounts.models import choices as ac_choices

import datetime


class UserFactory(dj_factory.DjangoModelFactory):

    username = factory.Faker("user_name")
    email = factory.Faker("email")

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
        datetime.datetime(2009, 1, 1, tzinfo=timezone.utc)
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


class TagFactory(dj_factory.DjangoModelFactory):

    name = factory.Faker("word")

    class Meta:
        model = Tag


class GreencheckFactory(dj_factory.DjangoModelFactory):

    hostingprovider = factory.Faker("random_int")
    greencheck_ip = factory.Faker("random_int")
    date = facfuzzy.FuzzyDateTime(datetime.datetime(2009, 1, 1, tzinfo=timezone.utc))
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
    # showonwebsite = models.BooleanField(verbose_name="Show on website", default=False)
    website = factory.Faker("domain_name")
    # datacenter = models.ManyToManyField(
    #     "Datacenter",
    #     through="HostingproviderDatacenter",
    #     through_fields=("hostingprovider", "datacenter"),
    #     related_name="hostingproviders",
    # )

    class Meta:
        model = ac_models.Hostingprovider


# @factory.django.mute_signals(post_save)
# class ProfileFactory(DjangoModelFactory):

#     # make a profile tied to a user
#     user = SubFactory(UserFactory)
#     phone = Faker("phone_number")
#     website = factory.LazyFunction(url_factory)
#     twitter = Faker("user_name")
#     facebook = Faker("user_name")
#     linkedin = Faker("user_name")
#     organisation = Faker("company")
#     bio = Faker("paragraph")
#     # tags = SubFactory(TagFactory)

#     user = factory.SubFactory("backend.users.tests.factories.UserFactory", profile=None)

#     class Meta:
#         model = Profile


# @factory.django.mute_signals(post_save)
# class FakePhotoProfileFactory(ProfileFactory):

#     photo = factory.LazyAttribute(
#         lambda o: ContentFile(
#             ImageFieldFactory()._make_data(
#                 {"width": 400, "height": 400, "format": "jpeg"}
#             ),
#             "test_pic.jpg",
#         )
#     )

#     class Meta:
#         model = Profile
