from django.db import models
from django.urls import reverse
from django_countries.fields import CountryField
from django.conf import settings
from django.core.exceptions import ValidationError
from taggit.managers import TaggableManager
from taggit.models import Tag
from apps.greencheck.models import IpAddressField
from apps.greencheck.validators import validate_ip_range
from model_utils.models import TimeStampedModel


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
    services = TaggableManager(
        verbose_name="Services offered",
        help_text="Click the services that your organisation offers. These will be listed in the green web directory.",
        blank=True,
    )

    def __str__(self) -> str:
        return f"{self.name}"

    def get_absolute_url(self) -> str:
        return reverse("provider_request_detail", args=[str(self.id)])

    @staticmethod
    def from_kwargs(**kwargs):
        pr_keys = ["name", "website", "description", "status", "created_by"]
        pr_data = {key: value for (key, value) in kwargs.items() if key in pr_keys}
        pr_data.setdefault("status", ProviderRequestStatus.OPEN.value)
        return ProviderRequest.objects.create(**pr_data)
    
    @classmethod
    def all_service_choices(cls):
        return [(tag, tag.name) for tag in Tag.objects.all()]
    
    def set_services(self, **kwargs):
        """
        Given list of IDs, apply matching services to ProviderRequest object
        """
        tag_ids = kwargs["services"]
        services = Tag.objects.filter(id__in=tag_ids)
        self.services.set(services)

    

class ProviderRequestLocation(models.Model):
    """
    Each ProviderRequest may be connected to many ProviderRequestLocations,
    in which the new provider offers services.
    """

    city = models.CharField(max_length=255)
    country = CountryField()
    request = models.ForeignKey(ProviderRequest, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.request.name} | {self.country}/{self.city}"

    @staticmethod
    def from_kwargs(**kwargs):
        location_keys = ["city", "country", "request"]
        location_data = {
            key: value for (key, value) in kwargs.items() if key in location_keys
        }
        return ProviderRequestLocation.objects.create(**location_data)


class ProviderRequestASN(models.Model):
    """
    ASN number that is available to the provider in a specific location.
    """

    asn = models.IntegerField()
    request = models.ForeignKey(ProviderRequest, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.asn}"


class ProviderRequestIPRange(models.Model):
    """
    IP range that is available to the provider in a specific location.
    """

    start = IpAddressField()
    end = IpAddressField()
    request = models.ForeignKey(ProviderRequest, on_delete=models.CASCADE)

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
    type = models.CharField(choices=EvidenceType.choices, max_length=255)
    request = models.ForeignKey(ProviderRequest, on_delete=models.CASCADE)

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
