from django.db import models
from django_countries.fields import CountryField
from django.conf import settings
from django.core.exceptions import ValidationError
from taggit.managers import TaggableManager
from apps.greencheck.models import IpAddressField
from apps.greencheck.validators import validate_ip_range
from model_utils.models import TimeStampedModel
from . import Hostingprovider


class ProviderRequestStatus(models.TextChoices):
    PENDING_REVIEW = "Pending review"  # GWF staff needs to verify the request
    ACCEPTED = "Accepted"  # GWF staff accepted the request
    REJECTED = "Rejected"  # GWF staff rejected the request (completely)
    OPEN = "Open"  # GWF staff requested some changes from the provider


class ProviderRequest(TimeStampedModel):
    name = models.CharField(max_length=255)
    website = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(choices=ProviderRequestStatus.choices, max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True
    )

    def __str__(self):
        return f"{self.name}"


class ProviderRequestSupplier(models.Model):
    supplier = models.ForeignKey(Hostingprovider, on_delete=models.CASCADE)
    # TODO: only allow services defined in the selected supplier
    services = TaggableManager()
    request = models.ForeignKey(ProviderRequest, on_delete=models.CASCADE, related_name="suppliers")

    def __str__(self):
        return f"{self.supplier}"

class ProviderRequestLocation(models.Model):
    city = models.CharField(max_length=255)
    country = CountryField()
    services = TaggableManager(
        verbose_name="Services Offered",
        help_text="Click the services that your organisation offers. These will be listed in the green web directory.",
        blank=True,
    )
    request = models.ForeignKey(ProviderRequest, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.request.name} | {self.country}/{self.city}"


class ProviderRequestASN(models.Model):
    asn = models.IntegerField()
    location = models.ForeignKey(ProviderRequestLocation, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.location} | {self.asn}"


class ProviderRequestIPRange(models.Model):
    start = IpAddressField()
    end = IpAddressField()
    location = models.ForeignKey(ProviderRequestLocation, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.location} | {self.start} - {self.end}"

    def clean(self):
        validate_ip_range(self.start, self.end)


class EvidenceType(models.TextChoices):
    ANNUAL_REPORT = "Annual report"
    WEB_PAGE = "Web page"
    CERTIFICATE = "Certificate"


class ProviderRequestEvidence(models.Model):
    title = models.CharField(max_length=255)
    link = models.URLField(null=True, blank=True)
    file = models.FileField(null=True, blank=True)
    location = models.ForeignKey(ProviderRequestLocation, on_delete=models.CASCADE)
    type = models.CharField(choices=EvidenceType.choices, max_length=255)

    def __str__(self):
        return f"{self.location} | {self.title}"

    def clean(self):
        reason = (
            "Exactly one of the value for the evidence, link or file, must be provided"
        )
        if self.link is None and self.file is None:
            raise ValidationError(f"{reason}. Neither of them were provided")
        if self.link and self.file:
            raise ValidationError(f"{reason}. Both of them were provided")
