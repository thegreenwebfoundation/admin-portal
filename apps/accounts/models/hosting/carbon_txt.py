from enum import StrEnum

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
from taggit import models as tag_models
from carbon_txt.finders import FileFinder
from carbon_txt.validators import CarbonTxtValidator
from carbon_txt.exceptions import UnreachableCarbonTxtFile
from httpx import HTTPError

from ...validators import DomainNameValidator

class CarbonTxtMotivation(tag_models.TagBase):
    """
    A model representing technical issues a provider might
    be suffering from which would motivate them to use carbon.txt
    as a solution.

    This would include things like:
     . "I use a Content Delivery Network (such as Cloudflare)"
     - "I resell services from another provider"
     -  "I have no fixed IP ranges or ASN"
     - "None of these apply to me"
    """

    show_description_field = models.BooleanField(
        default=False,
        verbose_name="Show the free-text description field when selected."
    )

    class Meta:
        verbose_name = _("Carbon.txt motivating issue")
        verbose_name_plural = _("Carbon.txt motivating issues")

class ProviderCarbonTxtMotivation(tag_models.TaggedItemBase):
    """
    The corresponding through model for linking a Provider to
    a CarbonTxtMotivation as above.
    """

    description = models.TextField(max_length=1000, null=True)

    content_object = models.ForeignKey(
        "Hostingprovider",
        on_delete=models.CASCADE,
    )
    tag = models.ForeignKey(
        CarbonTxtMotivation,
        related_name="%(app_label)s_%(class)s_items",
        on_delete=models.CASCADE,
    )

class ProviderCarbonTxt(TimeStampedModel):
    """
    The carbon.txt optionally associated with a provider,
    and used to resolve linked domains via DNS / HTTP header.
    """
    domain = models.CharField(max_length=255, unique=True, validators=[DomainNameValidator()])
    carbon_txt_url = models.URLField(max_length=512, unique=True, null=True)
    is_delegation_set = models.BooleanField(default=False)

    provider = models.OneToOneField(
        "Hostingprovider",
        on_delete=models.CASCADE,
        related_name="carbon_txt"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )

    class State(StrEnum):
        PENDING_VALIDATION="Pending validation"
        PENDING_DELEGATION="Pending delegation setup"
        ACTIVE="Active"

    class CarbonTxtValidationError(RuntimeError):
        message = "Error validating carbon.txt."

    class BlankDomainError(CarbonTxtValidationError):
        message = "You must provider a domain to validate!"

    class CarbonTxtNotValidatedError(CarbonTxtValidationError):
        message = "Could not find a valid carbon.txt at your domain."


    @classmethod
    def find_for_domain(cls, domain):
        """
        Method to identify if a valid provider carbon.txt exists for a given domain.
        First it performs a carbon.txt delegation lookup, attempting to resolve a canonical
        carbon.txt location for the domain. If this is found, it then checks for a
        ProviderCarbonTxt in our database corresponding to that url.
        In the case where a provider carbontxt exists, it is returned, otherwise
        returns None.
        """

        finder = FileFinder(http_timeout=settings.CARBON_TXT_RESOLUTION_TIMEOUT)
        try:
            result = finder.resolve_domain(domain)
            if result:
                return cls.objects.filter(carbon_txt_url=result.uri).first()
        except (UnreachableCarbonTxtFile, HTTPError):
            pass


    @property
    def state(self):
        """
        This state property represents the current state of the carbon.txt setup process.
        After confirming their domiain, the carbon.txt is in "pending validation" state,
        After confirming upload of their carbon_txt, it is in "pending delegation" state,
        and after confirming HTTP headers are set up, it becomes "active."
        """
        if self.carbon_txt_url is None:
            return self.State.PENDING_VALIDATION
        elif self.is_delegation_set is False:
            return self.State.PENDING_DELEGATION
        else:
            return self.State.ACTIVE

    @property
    def is_valid(self):
        """
        Whether or not this carbon.txt is valid for greencheck lookups - we should optionally
        use carbon.txts that have been validated to resolve greendomains, however it doesn't
        actually matter if the delegation flag has been set.
        """
        return self.state != self.State.PENDING_VALIDATION

    def validate(self):
        """
        Check that the domain is set, perform a carbon.txt lookup and validation against it,
        and, if succesfull, store the carbon_txt_url that it returns.
        """

        if self.domain is None or len(self.domain) == 0:
            raise self.BlankDomainError

        validator = CarbonTxtValidator(http_timeout=settings.CARBON_TXT_RESOLUTION_TIMEOUT)
        try:
            result = validator.validate_domain(self.domain)
            if len(result.exceptions) == 0:
                self.carbon_txt_url = result.url
                return True
            else:
                raise self.CarbonTxtNotValidatedError

        except (UnreachableCarbonTxtFile, HTTPError):
            raise self.CarbonTxtNotValidatedError


