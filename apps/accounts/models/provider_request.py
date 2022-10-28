from django.db import models
from django.urls import reverse
from django_countries.fields import CountryField
from django.conf import settings
from django.core.exceptions import ValidationError
from taggit.managers import TaggableManager
from apps.greencheck.models import IpAddressField
from apps.greencheck.validators import validate_ip_range
from model_utils.models import TimeStampedModel
from . import Hostingprovider


class ProviderRequestStatus(models.TextChoices):
    """
    Status of the ProviderRequest, exposed to both: end users and staff.
    Some status change (PENDING_REVIEW -> ACCEPTED) will be later used to trigger
    automatic creation of the different resources in the system.

    Meaning of each value:
    - PENDING_REVIEW: GWF staff needs to verify the request
    - ACCEPTED: GWF staff accepted the request
    - REJECTED: GWF staff rejected the request (completely)
    - OPEN: GWF staff requested some changes from the provider
    """

    PENDING_REVIEW = "Pending review"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"
    OPEN = "Open"


class ProviderRequest(TimeStampedModel):
    """
    Model representing the input data
    as submitted by the provider to our system,
    when they want to include their information into our dataset.

    """

    name = models.CharField(max_length=255)
    website = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(choices=ProviderRequestStatus.choices, max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True
    )

    def __str__(self) -> str:
        return f"{self.name}"

    def get_absolute_url(self) -> str:
        return reverse("provider_request_detail", args=[str(self.id)])


class ProviderRequestSupplier(models.Model):
    """
    Intermediate abstraction to model a relationship between:
    - a new ProviderRequest, and
    - existing Hostingprovider that supplies some services to them.
    """

    # TODO: add filtering and/or validation to check
    # that the selected services are offered by the selected supplier.

    supplier = models.ForeignKey(Hostingprovider, on_delete=models.CASCADE)
    services = TaggableManager(
        verbose_name="Services used",
        help_text="Click the services that your organisation uses from the selected supplier. These will be listed in the green web directory.",
        blank=True,
    )
    request = models.ForeignKey(
        ProviderRequest, on_delete=models.CASCADE, related_name="suppliers"
    )

    def __str__(self) -> str:
        return f"{self.supplier}"


class ProviderRequestLocation(models.Model):
    """
    Each ProviderRequest may be connected to many ProviderRequestLocations,
    in which the new provider offers services.
    """

    city = models.CharField(max_length=255)
    country = CountryField()
    services = TaggableManager(
        verbose_name="Services offered",
        help_text="Click the services that your organisation offers. These will be listed in the green web directory.",
        blank=True,
    )
    request = models.ForeignKey(ProviderRequest, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.request.name} | {self.country}/{self.city}"


class ProviderRequestASN(models.Model):
    """
    ASN number that is available to the provider in a specific location.
    """

    asn = models.IntegerField()
    location = models.ForeignKey(ProviderRequestLocation, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.asn}"


class ProviderRequestIPRange(models.Model):
    """
    IP range that is available to the provider in a specific location.
    """

    start = IpAddressField()
    end = IpAddressField()
    location = models.ForeignKey(ProviderRequestLocation, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.start} - {self.end}"

    def clean(self) -> None:
        validate_ip_range(self.start, self.end)


class EvidenceType(models.TextChoices):
    """
    Type of the supporting evidence, that certifies that green energy is used
    """

    ANNUAL_REPORT = "Annual report"
    WEB_PAGE = "Web page"
    CERTIFICATE = "Certificate"


class ProviderRequestEvidence(models.Model):
    """
    Document that certifies that green energy is used in a specific location
    operated by the provider.
    """

    title = models.CharField(max_length=255)
    link = models.URLField(null=True, blank=True)
    file = models.FileField(null=True, blank=True)
    location = models.ForeignKey(ProviderRequestLocation, on_delete=models.CASCADE)
    type = models.CharField(choices=EvidenceType.choices, max_length=255)

    def __str__(self) -> str:
        return f"{self.title} ({self.type})"

    def clean(self) -> None:
        reason = (
            "Exactly one of the value for the evidence, link or file, must be provided"
        )
        if self.link is None and not bool(self.file):
            raise ValidationError(f"{reason}. Neither of them were provided")
        if self.link and bool(self.file):
            raise ValidationError(f"{reason}. Both of them were provided")
