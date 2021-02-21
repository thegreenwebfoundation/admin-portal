import logging

from django.db import models
from django.conf import settings
from django_countries.fields import CountryField
from django_mysql.models import EnumField
from anymail.message import AnymailMessage
from django.template.loader import render_to_string

from model_utils.models import TimeStampedModel

from .choices import (
    EnergyType,
    TempType,
    ModelType,
    PartnerChoice,
    ClassificationChoice,
    CoolingChoice,
)
from apps.greencheck.choices import (
    StatusApproval,
    ActionChoice,
)

logger = logging.getLogger(__name__)


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
        to review the IP Range or AS network.
        """
        hosting_provider = approval_request.hostingprovider
        logger.debug(f"Approval request: {approval_request} for {hosting_provider}")

        if self.needs_review(approval_request):
            return self.flag_for_review(approval_request)

    def needs_review(self, approval_request=None):
        """
        Checks if the hosting provider has outstanding submissions
        from partners to review, and returns either True if so, or
        false if not.
        """
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

        # if the provided approval new, and not seen before?
        # return true if so, otherwise assume this is not new
        if approval_request is None:
            return False

        if approval_request not in approval_requests:
            return True

        return False

    def flag_for_review(self, approval_request):
        """
        Mark this hosting provider as in need of review by admins.
        Sends an notification via email to admins.
        """

        #  notify_admin_via_email(approval_request)
        provider = approval_request.hostingprovider
        ctx = {"approval_request": approval_request, "provider": provider}
        notification_subject = f"TGWF: {approval_request.hostingprovider} - has been updated and needs a review"

        notification_email_copy = render_to_string("flag_for_review_text.txt", ctx)

        msg = AnymailMessage(
            subject=notification_subject,
            body=notification_email_copy,
            to=["support@thegreenwebfoundation.org"],
        )

        # this adds the HTML version we've rendered
        # msg.attach_alternative(generated_html, "text/html")
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
