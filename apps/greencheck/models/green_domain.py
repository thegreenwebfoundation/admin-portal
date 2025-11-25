import logging
import typing
from datetime import datetime

from django.db import models
from django.core.serializers import serialize
from django.utils import timezone
from django_mysql import models as dj_mysql_models

from ...accounts import models as ac_models
from .. import choices as gc_choices
from ..network_utils import validate_domain

from .green_domain_badge import GreenDomainBadge
from .green_check import Greencheck

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
    def green_domain_for(cls, url, skip_cache=False):
        """
        This is the principal method to look up a domain for checking, using the cache.
        It validates the URL, then EITHER returns a cached greendomain result, OR performs a full
        lookup, if no cached result is availble (or if the caller has passed the skip_cache flag).
        Green results are cached to the greendomains table, while grey results are returned without saving.
        """
        from ..domain_check import GreenDomainChecker # Prevent circular import error
        checker = GreenDomainChecker()
        try:
            domain = validate_domain(url)
        except Exception as ex:
            # not a valid domain, OR a valid IP. Get rid of it.
            logger.warning(f"unable to extract domain from {url}, exception was: {ex}")
            return cls.grey_result(url)

        if skip_cache:
            cls.clear_from_all_caches(domain)
        else:
            # Try the database green domain cache table first:
            if green_domain := cls.objects.filter(url=domain).first():
                Greencheck.log_greendomain_asynchronous(green_domain)
                return green_domain

        # Otherwise, there is no cached domain OR we are explicitly refreshing the cache,
        # try full lookup using network:
        sitecheck = checker.check_domain(domain, refresh_carbon_txt_cache=skip_cache)
        Greencheck.log_sitecheck_asynchronous(sitecheck)
        if sitecheck.green:
            green_domain = cls.from_sitecheck(sitecheck)
            green_domain.save()
            return green_domain
        else:
            return cls.grey_result(domain=sitecheck.url)

    @classmethod
    def grey_result(cls, domain=None, type=gc_choices.GreenlistChoice.NONE.value):
        """
        Return a grey domain with just the domain name added,
        the time of the and the rest empty.
        """
        modified = ac_models.CarbonTxtDomainResultCache.last_modified(domain) or timezone.now()
        return GreenDomain(
            green=False,
            url=domain,
            hosted_by=None,
            hosted_by_id=None,
            hosted_by_website=None,
            listed_provider=False,
            partner=None,
            type=type,
            modified=modified,
        )

    @classmethod
    def from_sitecheck(cls, sitecheck):
        """
        Return a greendomain model for a given sitecheck. Note that this can represent
        either a green or a grey domain, depending on the result of the sitecheck itself.
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
    def clear_from_all_caches(cls, domain):
        """
        Clear any trace of a domain from local caches.
        """
        cls.clear_cache(domain)
        GreenDomainBadge.clear_cache(domain)
        ac_models.CarbonTxtDomainResultCache.clear_cache(domain)

    @classmethod
    def clear_cache(cls, domain):
        if obj := cls.objects.filter(url=domain).first():
            obj.delete()

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


