import logging
import typing
from datetime import datetime

from django.db import models
from django.core.serializers import serialize
from django.utils import timezone
from django_mysql import models as dj_mysql_models

from ...accounts import models as ac_models
from .. import choices as gc_choices

logger = logging.getLogger(__name__)

class GreenDomain(models.Model):
    """
    The model we use for quick lookups against a domain.

    """

    url = models.CharField(max_length=255)
    hosted_by_id = models.IntegerField()
    hosted_by = models.CharField(max_length=255)
    hosted_by_website = models.CharField(max_length=255)
    listed_provider = models.BooleanField()
    partner = models.CharField(max_length=255)
    green = models.BooleanField()
    modified = models.DateTimeField()
    created = models.DateTimeField(auto_now_add=True)
    type = dj_mysql_models.EnumField(
        choices=gc_choices.GreenlistChoice.choices,
        default=gc_choices.GreenlistChoice.NONE,
    )

    def __str__(self):
        return f"{self.url} - {self.modified}"

    # Factories
    @classmethod
    def create_for_provider(cls, domain: str, provider: ac_models.Hostingprovider, type=gc_choices.GreenlistChoice.NONE.value):
        """
        Create a new green domain for the domain passed in,  and allocate
        it  to the given provider.
        """

        dom = GreenDomain(
            green=True,
            url=domain,
            hosted_by=provider.name,
            hosted_by_id=provider.id,
            hosted_by_website=provider.website,
            listed_provider=provider.is_listed,
            partner=ac_models.PartnerChoice.NONE,
            modified=timezone.now(),
            type=type,
        )
        dom.save()
        return dom

    @classmethod
    def upsert_for_provider(cls, domain: str, provider: ac_models.Hostingprovider, type=gc_choices.GreenlistChoice.NONE.value):
        """
        Try to fetch given domain if it exists, and link it given provider,
        otherwise create a new green domain, allocated to said provider.
        """
        try:
            green_domain = GreenDomain.objects.get(url=domain)
            green_domain.allocate_to_provider(provider, type)
        except GreenDomain.DoesNotExist:
            green_domain = GreenDomain.create_for_provider(domain, provider, type)

        return green_domain

    @classmethod
    def grey_result(cls, domain=None, type=gc_choices.GreenlistChoice.NONE.value):
        """
        Return a grey domain with just the domain name added,
        the time of the and the rest empty.
        """
        return GreenDomain(
            green=False,
            url=domain,
            hosted_by=None,
            hosted_by_id=None,
            hosted_by_website=None,
            listed_provider=False,
            partner=None,
            type=type,
            modified=timezone.now(),
        )

    @classmethod
    def from_sitecheck(cls, sitecheck):
        """
        Return a grey domain with just the domain name added,
        the time of the and the rest empty.
        """
        hosting_provider = None
        try:
            hosting_provider = ac_models.Hostingprovider.objects.get(
                pk=sitecheck.hosting_provider_id
            )
        except ac_models.Hostingprovider.DoesNotExist:
            logger.warning(
                ("We expected to find a provider for this sitecheck, But didn't. ")
            )
            return cls.grey_result(domain=sitecheck.url)

        return GreenDomain(
            url=sitecheck.url,
            hosted_by=hosting_provider.name,
            hosted_by_id=hosting_provider.id,
            hosted_by_website=hosting_provider.website,
            partner=hosting_provider.partner,
            listed_provider=hosting_provider.is_listed,
            modified=timezone.now(),
            green=True,
            type=sitecheck.match_type,
        )

    @classmethod
    def clear_cache(cls, domain):
        if obj := cls.objects.filter(url=domain).first():
            obj.delete()


    @classmethod
    def from_serializable_dict(cls, serialized):
        created = serialized.get("created") and datetime.fromisoformat(serialized["created"])
        modified = serialized.get("modified") and datetime.fromisoformat(serialized["modified"])
        kwargs = {
            **serialized,
            **{ "created": created, "modified": modified }
        }
        return cls(**kwargs)

    def to_serializable_dict(self):
        serialized = serialize("python", [self])[0]
        attributes = serialized["fields"]
        created = attributes.get("created") and attributes["created"].isoformat()
        modified = attributes.get("modified") and attributes["modified"].isoformat()
        id = serialized.get("pk")
        return {
            **attributes,
            **{ "id": id, "created": created, "modified":  modified }
        }

    # Queries
    @property
    def hosting_provider(self) -> typing.Union[ac_models.Hostingprovider, None]:
        """
        Try to find the corresponding hosting provider for this url.
        Return either the hosting providr
        """
        try:
            return ac_models.Hostingprovider.objects.get(pk=self.hosted_by_id)
        except ac_models.Hostingprovider.DoesNotExist:
            return None
        except ValueError:
            return None
        except Exception as err:
            logger.warn(
                (
                    f"Couldn't find a hosting provider for url: {self.url}, "
                    f"and hosted_by_id: {self.hosted_by_id}."
                )
            )
            logger.warn(err)
            return None

    @property
    def added_via_carbontxt(self) -> bool:
        """
        Return True if this domain is linked to a provider via a
        linked domain, otherwise return false.
        """
        return self.type == gc_choices.GreenlistChoice.CARBONTXT.value

    @classmethod
    def check_for_domain(cls, domain, skip_cache=False, refresh_carbon_txt_cache=None):
        """
        Accept a domain, or object that resolves to an IP and check.
        Accepts skip_cache option to perform a full DNS lookup
        instead of looking up a domain by key.
        We also allow the main greendomains cache to be skipped, while NOT
        skipping the separate carbon.txt domain cache - this is used in the
        carbon.txt image generation view, as image embed code has historiclaly been provided
        to end users **with** the nocache parameter set, and we want to ensure that the carbon.txt
        cache is **not** skipped, even in this case.
        """
        from ..domain_check import GreenDomainChecker

        checker = GreenDomainChecker()

        if refresh_carbon_txt_cache is None:
            refresh_carbon_txt_cache = skip_cache

        if skip_cache:
            return checker.perform_full_lookup(domain, refresh_carbon_txt_cache=refresh_carbon_txt_cache)

        return GreenDomain.objects.filter(url=domain).first()

    # Mutators
    def allocate_to_provider(self, provider: ac_models.Hostingprovider, type=gc_choices.GreenlistChoice.NONE.value):
        """
        Accept a provider and update the green domain to show as hosted by
        it in future checks.
        """
        self.hosted_by_id = provider.id
        self.hosted_by = provider.name
        self.hosted_by_website = provider.website
        self.modified = timezone.now()
        self.type = type
        self.save()

        # add log entry for making this change

    class Meta:
        db_table = "greendomain"


