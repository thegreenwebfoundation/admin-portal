from django.db import models
from django_countries.fields import CountryField
from django.conf import settings
from taggit.managers import TaggableManager
from apps.greencheck.models import IpAddressField
from model_utils.models import TimeStampedModel


class ProviderRequestStatus(models.TextChoices):
    PENDING_REVIEW = "Pending review"  # GWF staff needs to verify the request
    ACCEPTED = "Accepted"  # GWF staff accepted the request
    REJECTED = "Rejected"  # GWF staff rejected the request (completely)
    OPEN = (
        "Open"  # GWF staff requested some changes from the provider
    )


class ProviderRequest(TimeStampedModel):
    name = models.CharField(max_length=255)
    website = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(choices=ProviderRequestStatus.choices, max_length=255)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)


class ProviderRequestLocation(models.Model):
    city = models.CharField(max_length=255)
    country = CountryField()
    services = TaggableManager(
        verbose_name="Services Offered",
        help_text="Click the services that your organisation offers. These will be listed in the green web directory.",
        blank=True,
    )
    request = models.ForeignKey(ProviderRequest, on_delete=models.CASCADE)


class ProviderRequestASN(models.Model):
    asn = models.IntegerField()
    location = models.ForeignKey(ProviderRequestLocation, on_delete=models.CASCADE)


class ProviderRequestIPRange(models.Model):
    start = IpAddressField()
    end = IpAddressField()
    location = models.ForeignKey(ProviderRequestLocation, on_delete=models.CASCADE)


class EvidenceType(models.TextChoices):
    ANNUAL_REPORT = "Annual report"
    WEB_PAGE = "Web page"
    CERTIFICATE = "Certificate"


class ProviderRequestEvidence(models.Model):
    title = models.CharField(max_length=255)
    # TODO: add validation: link XOR file
    link = models.URLField(null=True)
    file = models.FileField()
    location = models.ForeignKey(ProviderRequestLocation, on_delete=models.CASCADE)
    type = models.CharField(choices=EvidenceType.choices, max_length=255)
