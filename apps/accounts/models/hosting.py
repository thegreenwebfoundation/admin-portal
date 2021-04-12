import logging

from django.db import models
from django.conf import settings
from django_countries.fields import CountryField
from django.urls import reverse
from django_mysql.models import EnumField
from anymail.message import AnymailMessage
from django.utils import timezone
from django.template.loader import render_to_string
from haikunator import Haikunator
from taggit.managers import TaggableManager


from model_utils.models import TimeStampedModel

from .choices import (
    EnergyType,
    TempType,
    ModelType,
    PartnerChoice,
    ClassificationChoice,
    CoolingChoice,
)
from apps.greencheck.choices import StatusApproval

logger = logging.getLogger(__name__)

haikunator = Haikunator()


class Datacenter(models.Model):
    country = CountryField(db_column="countrydomain")

    dc12v = models.BooleanField()
    greengrid = models.BooleanField()
    mja3 = models.BooleanField(null=True, verbose_name="meerjaren plan energie 3")
    model = models.CharField(max_length=255, choices=ModelType.choices)
    name = models.CharField(max_length=255, db_column="naam")
    pue = models.FloatField(verbose_name="Power usage effectiveness")
    residualheat = models.BooleanField(null=True)
    showonwebsite = models.BooleanField(verbose_name="Show on website", default=False)
    temperature = models.IntegerField(null=True)
    temperature_type = models.CharField(
        max_length=255, choices=TempType.choices, db_column="temperaturetype"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    virtual = models.BooleanField()
    website = models.CharField(max_length=255)

    def legacy_representation(self):
        """
        Return a dictionary representation of datacentre,
        suitable for serving in the older directory
        API.
        """

        # {
        #     "id": "28",
        #     "naam": "Website Dataport",
        #     "website": "http://www.website.co.uk",
        #     "countrydomain": "UK",
        #     "model": "groeneenergie",
        #     "pue": "1.2",
        #     "mja3": "0",
        #     "city": "Ballasalla",
        #     "country": "Isle of Man",
        #     "classification": null,
        #     "certificates": [],
        #     "classifications": [],
        # }
        return {
            "id": self.id,
            "naam": self.name,
            "website": self.website,
            "countrydomain": str(self.country),
            "model": self.model,
            "pue": self.pue,
            "mja3": self.mja3,
            # this needs a new table we don't have
            "city": "NOT IMPLEMENTED",
            "country": "NOT IMPLEMENTED",
            "classification": "NOT IMPLEMENTED",
            # this lists through DatacenterCertificate
            "certificates": ["NOT IMPLEMENTED"],
            # this lists through DatacenterClassification
            "classifications": ["NOT IMPLEMENTED"],
        }

    def __str__(self):
        return self.name

    class Meta:
        db_table = "datacenters"
        indexes = [
            models.Index(fields=["name"], name="name"),
        ]
        # managed = False


class DatacenterClassification(models.Model):
    # TODO if this is used to some extent, this should be m2m
    classification = models.CharField(max_length=255, choices=ClassificationChoice)
    datacenter = models.ForeignKey(
        Datacenter,
        db_column="id_dc",
        on_delete=models.CASCADE,
        related_name="classifications",
    )

    def __str__(self):
        return f"{self.classification} - related id: {self.datacenter_id}"

    class Meta:
        db_table = "datacenters_classifications"
        # managed = False


class DatacenterCooling(models.Model):
    # TODO if this is used to some extent, this should ideally be m2m
    cooling = models.CharField(max_length=255, choices=CoolingChoice.choices)
    datacenter = models.ForeignKey(
        Datacenter, db_column="id_dc", on_delete=models.CASCADE
    )

    def __str__(self):
        return self.cooling

    class Meta:
        db_table = "datacenters_coolings"
        # managed = False


class Hostingprovider(models.Model):
    archived = models.BooleanField(default=False)
    country = CountryField(db_column="countrydomain")
    customer = models.BooleanField(default=False)
    icon = models.CharField(max_length=50, blank=True)
    iconurl = models.CharField(max_length=255, blank=True)
    model = EnumField(choices=ModelType.choices, default=ModelType.compensation)
    name = models.CharField(max_length=255, db_column="naam")
    partner = models.CharField(
        max_length=255,
        null=True,
        default=PartnerChoice.none,
        choices=PartnerChoice.choices,
        blank=True,
    )
    services = TaggableManager(
        verbose_name="Services Offered",
        help_text="Click the services that your organisation offers. These will be listed in the green web directory.",
    )
    showonwebsite = models.BooleanField(verbose_name="Show on website", default=False)
    website = models.CharField(max_length=255)
    datacenter = models.ManyToManyField(
        "Datacenter",
        through="HostingproviderDatacenter",
        through_fields=("hostingprovider", "datacenter"),
        related_name="hostingproviders",
    )

    def __str__(self):
        return self.name

    def mark_as_pending_review(self, approval_request):
        """
        Accept an approval request, and if the hosting provider
        doesn't already have outstanding approvals, notify admins
        to review the IP Range or AS network. Returns true if
        marking it as pending trigger action, otherwise false.
        """
        hosting_provider = approval_request.hostingprovider
        logger.debug(f"Approval request: {approval_request} for {hosting_provider}")

        approval_requests = self.outstanding_approval_requests()

        if approval_request not in approval_requests:
            self.flag_for_review(approval_request)
            return True

        return False

    def outstanding_approval_requests(self):
        """
        Return all the ASN or IP Range requests as a single list.
        """
        logger.debug(self.greencheckasnapprove_set.all())
        logger.debug(self.greencheckipapprove_set.all())
        outstanding_asn_approval_reqs = self.greencheckasnapprove_set.filter(
            status__in=[StatusApproval.new, StatusApproval.update]
        )
        outstanding_ip_range_approval_reqs = self.greencheckipapprove_set.filter(
            status__in=[StatusApproval.new, StatusApproval.update]
        )
        # use list() to evalute the queryset to a datastructure that
        # we can concatenate easily
        approval_requests = list(outstanding_asn_approval_reqs) + list(
            outstanding_ip_range_approval_reqs
        )
        return approval_requests

    def flag_for_review(self, approval_request):
        """
        Mark this hosting provider as in need of review by admins.
        Sends an notification via email to admins.
        """

        #  notify_admin_via_email(approval_request)
        provider = approval_request.hostingprovider
        link_path = reverse(
            "greenweb_admin:accounts_hostingprovider_change", args=[provider.id]
        )
        link_url = f"{settings.SITE_URL}{link_path}"
        ctx = {
            "approval_request": approval_request,
            "provider": provider,
            "link_url": link_url,
        }
        notification_subject = (
            f"TGWF: {approval_request.hostingprovider} - "
            "has been updated and needs a review"
        )

        notification_email_copy = render_to_string("flag_for_review_text.txt", ctx)
        notification_email_html = render_to_string("flag_for_review_text.html", ctx)

        msg = AnymailMessage(
            subject=notification_subject,
            body=notification_email_copy,
            to=["support@thegreenwebfoundation.org"],
        )

        msg.attach_alternative(notification_email_html, "text/html")
        msg.send()

    class Meta:
        # managed = False
        verbose_name = "Hosting Provider"
        db_table = "hostingproviders"
        indexes = [
            models.Index(fields=["name"], name="name"),
            models.Index(fields=["archived"], name="archived"),
            models.Index(fields=["showonwebsite"], name="showonwebsite"),
        ]


class HostingCommunication(TimeStampedModel):
    template = models.CharField(max_length=128)
    hostingprovider = models.ForeignKey(
        Hostingprovider, null=True, on_delete=models.SET_NULL
    )


class HostingproviderDatacenter(models.Model):
    """Intermediary table between Datacenter and Hostingprovider"""

    approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    datacenter = models.ForeignKey(Datacenter, null=True, on_delete=models.CASCADE)
    hostingprovider = models.ForeignKey(
        Hostingprovider, null=True, on_delete=models.CASCADE
    )

    class Meta:
        db_table = "datacenters_hostingproviders"
        # managed = False


class AbstractSupportingDocument(models.Model):
    """
    When a hosting provider makes claims about running on green energy,
    offsetting their emissions, and so on want to them to upload the
    evidence.
    We subclass this

    """

    title = models.CharField(
        max_length=255,
        help_text="Describe what you are listing, as you would to a user or customer.",
    )
    attachment = models.FileField(
        upload_to="uploads/",
        blank=True,
        help_text="If you have a sustainability report, or bill from a energy provider provider, or similar certificate of supply from a green tariff add it here.",
    )
    url = models.URLField(
        blank=True,
        help_text="Alternatively, if you add a link, we'll fetch a copy at the URL you list, so we can point to the version when you listed it",
    )
    description = models.TextField(blank=True,)
    valid_from = models.DateField()
    valid_to = models.DateField()

    public = models.BooleanField(
        default=True,
        help_text=(
            "If this is checked, we'll add a link to this "
            "document/page in your entry in the green web directory."
        ),
    )

    def __str__(self):
        return f"{self.valid_from} - {self.title}"

    class Meta:
        abstract = True
        verbose_name = "Supporting Document"


class DatacentreSupportingDocument(AbstractSupportingDocument):
    """
    The concrete class for datacentre providers.
    """

    datacenter = models.ForeignKey(
        Datacenter,
        db_column="id_dc",
        null=True,
        on_delete=models.CASCADE,
        related_name="datacenter_evidence",
    )

    @property
    def parent(self):
        return self.datacentre


class HostingProviderSupportingDocument(AbstractSupportingDocument):
    """
    The subclass for hosting providers.
    """

    hostingprovider = models.ForeignKey(
        Hostingprovider,
        db_column="id_hp",
        null=True,
        on_delete=models.CASCADE,
        related_name="hostingprovider_evidence",
    )

    @property
    def parent(self):
        return self.hostingprovider


class Certificate(models.Model):
    energyprovider = models.CharField(max_length=255)
    mainenergy_type = models.CharField(
        max_length=255, db_column="mainenergytype", choices=EnergyType.choices
    )
    url = models.CharField(max_length=255)
    valid_from = models.DateField()
    valid_to = models.DateField()

    class Meta:
        abstract = True


class DatacenterCertificate(Certificate):
    datacenter = models.ForeignKey(
        Datacenter,
        db_column="id_dc",
        null=True,
        on_delete=models.CASCADE,
        related_name="datacenter_certificates",
    )

    class Meta:
        db_table = "datacenter_certificates"
        # managed = False


class HostingproviderCertificate(Certificate):
    hostingprovider = models.ForeignKey(
        Hostingprovider,
        db_column="id_hp",
        null=True,
        on_delete=models.CASCADE,
        related_name="hostingprovider_certificates",
    )

    class Meta:
        db_table = "hostingprovider_certificates"
        # managed = False


class HostingproviderStats(models.Model):
    hostingprovider = models.ForeignKey(
        Hostingprovider,
        on_delete=models.CASCADE,
        db_column="id_hp",
        # this column is the foreigh key for hosting providers
        # AND considered the primary key. Without this extra keyword,
        # we get crashes when deleting hosting providers
        primary_key=True,
    )
    green_domains = models.IntegerField()
    green_checks = models.IntegerField()

    class Meta:
        db_table = "hostingproviders_stats"
        # managed = False
