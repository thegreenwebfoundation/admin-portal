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
from typing import Iterable, Tuple, List


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
    authorised_by_org = models.BooleanField()
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
    def from_kwargs(**kwargs) -> "ProviderRequest":
        """
        Given arbitrary kwargs, construct a new ProviderRequest object.
        No validation is performed on the created object.
        """
        pr_keys = [
            "name",
            "website",
            "description",
            "status",
            "created_by",
            "authorised_by_org",
        ]
        pr_data = {key: value for (key, value) in kwargs.items() if key in pr_keys}
        pr_data.setdefault("status", ProviderRequestStatus.OPEN.value)
        return ProviderRequest.objects.create(**pr_data)

    def set_services_from_slugs(self, service_slugs: Iterable[str]) -> None:
        """
        Given list of service slugs (corresponding to Tag slugs)
        apply matching services to the ProviderRequest object
        """
        services = Tag.objects.filter(slug__in=service_slugs)
        self.services.set(services)

    @classmethod
    def get_service_choices(cls) -> List[Tuple[int, str]]:
        """
        Returns a list of available services (implemented in the Tag model)
        in a format expected by ChoiceField
        """
        return [(tag.slug, tag.name) for tag in Tag.objects.all()]


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
    def from_kwargs(**kwargs) -> "ProviderRequestLocation":
        """
        Given arbitrary kwargs, construct a new ProviderRequestLocation object.
        No validation is performed on the created object.
        """
        location_keys = ["city", "country", "request"]
        location_data = {
            key: value for (key, value) in kwargs.items() if key in location_keys
        }
        return ProviderRequestLocation.objects.create(**location_data)


class ProviderRequestASN(models.Model):
    """
    ASN number that is operated by the provider.
    """

    asn = models.IntegerField()
    request = models.ForeignKey(ProviderRequest, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.asn}"


class ProviderRequestIPRange(models.Model):
    """
    IP range that is operated by the provider.
    """

    start = IpAddressField()
    end = IpAddressField()
    request = models.ForeignKey(ProviderRequest, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.start} - {self.end}"

    def clean(self) -> None:
        return validate_ip_range(self.start, self.end)


class EvidenceType(models.TextChoices):
    """
    Type of the supporting evidence, that certifies that green energy is used
    """

    ANNUAL_REPORT = "Annual report"
    WEB_PAGE = "Web page"
    CERTIFICATE = "Certificate"
    OTHER = "Other"


class ProviderRequestEvidence(models.Model):
    """
    Document that certifies that green energy is used by the provider.
    A single evidence is either a web link or a file.
    """

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    link = models.URLField(null=True, blank=True)
    file = models.FileField(null=True, blank=True)
    type = models.CharField(choices=EvidenceType.choices, max_length=255)
    public = models.BooleanField(default=True)
    request = models.ForeignKey(ProviderRequest, on_delete=models.CASCADE)

    def __str__(self) -> str:
        name = f"{self.title}, {self.type}"
        if self.public:
            return f"{name}, public"
        return f"{name}, private"

    def clean(self) -> None:
        reason = "Provide a link OR a file on each row"
        if self.link is None and not bool(self.file):
            raise ValidationError(f"{reason}, you haven't submitted either.")
        if self.link and bool(self.file):
            raise ValidationError(
                f"{reason}, you've attempted to submit both - we've removed the file for now."
            )
