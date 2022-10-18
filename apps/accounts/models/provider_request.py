from django.db import models
from django_countries.fields import CountryField
from taggit.managers import TaggableManager
from greencheck.models import IpAddressField


class ProviderRequestStatus(models.TextChoices):
    # TODO: naming is hard
    PENDING_REVIEW = "Pending review"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"
    CHANGES_REQUESTED = "Changes requested"


class ProviderRequest(models.Model):
    name = models.CharField(max_length=255)
    website = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(choices=ProviderRequestStatus.choices)


class ProviderRequestASN(models.Model):
    asn = models.IntegerField()
    request = models.ForeignKey(ProviderRequest)


class ProviderRequestIPRange(models.Model):
    start = IpAddressField()
    end = IpAddressField()
    request = models.ForeignKey(ProviderRequest)


class ProviderRequestLocation(models.Model):
    city = models.CharField()
    country = CountryField()
    services = TaggableManager(
        verbose_name="Services Offered",
        help_text="Click the services that your organisation offers. These will be listed in the green web directory.",
        blank=True,
    )
    request = models.ForeignKey(ProviderRequest)


class EvidenceType(models.TextChoices):
    ANNUAL_REPORT = "Annual report"
    WEB_PAGE = "Web page"
    CERTIFICATE = "Certificate"


class ProviderRequestEvidence(models.Model):
    title = models.CharField()
    # TODO: can link and file be modelled as one, preferably existing abstraction?
    link = models.URLField()
    file = models.FileField()
    location = models.ForeignKey(ProviderRequestLocation)
    type = models.CharField(choices=EvidenceType.choices)
