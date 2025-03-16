import datetime
import hashlib
import logging
import secrets
import typing
from urllib.parse import urlparse

from anymail.message import AnymailMessage
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from django_mysql.models import EnumField
from guardian.shortcuts import get_users_with_perms
from model_utils.models import TimeStampedModel
from taggit import models as tag_models
from taggit.managers import TaggableManager

from apps.greencheck.choices import GreenlistChoice, StatusApproval
from apps.greencheck.exceptions import NoSharedSecret

from ..permissions import manage_datacenter, manage_provider
from .choices import (
    ClassificationChoice,
    CoolingChoice,
    EnergyType,
    ModelType,
    PartnerChoice,
    TempType,
)

# import apps.greencheck.models as gc_models


logger = logging.getLogger(__name__)


GREEN_VIA_CARBON_TXT = f"green:{GreenlistChoice.CARBONTXT.value}"
AWAITING_REVIEW_STRING = "Awaiting Review"
AWAITING_REVIEW_SLUG = "awaiting-review"


# this allows us to identify:
# 1. the issuer of the hash (i.e. Green Web Foundation)
# 2. the version of the algorithm used to create the hash
# if we update the algorithm in the future, we would increment
# the version. This also allows for quickly identifing key info
# about the hash
DOMAIN_HASH_ISSUER_ID = "GWF-01"


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
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    virtual = models.BooleanField()
    website = models.CharField(max_length=255)

    @property
    def users(self) -> models.QuerySet["User"]:
        """
        Returns a QuerySet of Users who have permissions for a given Datacenter
        """
        return get_users_with_perms(
            self, only_with_perms_in=(manage_datacenter.codename,)
        )

    @property
    def users_explicit_perms(self) -> models.QuerySet["User"]:
        """
        Returns a QuerySet of all Users that have *explicit* permissions to manage this Datacenter,
        not taking into consideration:
            - group membership
            - superuser status
        """
        return get_users_with_perms(
            self,
            only_with_perms_in=(manage_datacenter.codename,),
            with_superusers=False,
            with_group_users=False,
        )

    @property
    def admin_url(self) -> str:
        return reverse("greenweb_admin:accounts_datacenter_change", args=[str(self.id)])

    @property
    def city(self):
        """
        Return the city this datacentre is
        placed in.
        """
        location = self.datacenterlocation_set.first()
        if location:
            return location.city
        else:
            return None

    def legacy_representation(self):
        """
        Return a dictionary representation of datacentre,
        suitable for serving in the older directory
        API.
        """

        certificates = [
            cert.legacy_representation() for cert in self.datacenter_certificates.all()
        ]

        return {
            "id": self.id,
            "naam": self.name,
            "website": self.website,
            "countrydomain": str(self.country),
            "model": self.model,
            "pue": self.pue,
            "mja3": self.mja3,
            # this needs a new table we don't have
            "city": self.city,
            "country": self.country.name,
            # this lists through DatacenterCertificate
            "certificates": certificates,
            # the options below are deprecated
            "classification": "DEPRECATED",
            # this lists through DatacenterClassification
            "classifications": ["DEPRECATED"],
        }

    def __str__(self):
        return self.name

    class Meta:
        db_table = "datacenters"
        indexes = [
            models.Index(fields=["name"], name="dc_name"),
        ]
        permissions = (manage_datacenter.astuple(),)


class DatacenterClassification(models.Model):
    # TODO if this is used to some extent, this should be m2m
    classification = models.CharField(
        max_length=255, choices=ClassificationChoice.choices
    )
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


class Label(tag_models.TagBase):
    """
    The base tag class we need in order to create a separate set of
    tags to use as internal labels
    """

    class Meta:
        verbose_name = _("Label")
        verbose_name_plural = _("Labels")


class ProviderLabel(tag_models.TaggedItemBase):
    """
    A different through model for listing internally facing tags,
    to help us categorise and segment providers.
    """

    content_object = models.ForeignKey(
        "Hostingprovider",
        on_delete=models.CASCADE,
    )
    tag = models.ForeignKey(
        Label,
        related_name="%(app_label)s_%(class)s_items",
        on_delete=models.CASCADE,
    )


class Service(tag_models.TagBase):
    """
    A model representing the kinds of (hosted) services a provider
    offers.

    This would include things like "colocation services",
    "virtual private servers", "shared hosting" and so on.
    A subclass of Taggit's `TagBase` model.
    """

    class Meta:
        verbose_name = _("Service")
        verbose_name_plural = _("Services")


class ProviderService(tag_models.TaggedItemBase):
    """
    The corresponding through model for linking a Provider to
    a Service as outlined above.
    """

    content_object = models.ForeignKey(
        "Hostingprovider",
        on_delete=models.CASCADE,
    )
    tag = models.ForeignKey(
        Service,
        related_name="%(app_label)s_%(class)s_items",
        on_delete=models.CASCADE,
    )


class DomainHash(TimeStampedModel):
    """
    A domain hash is unique to a combination of a domain and a provider.
    It is used to verify that a domain is hosted by a provider, and referred to when
    the platform is looking up a specific domain to see if a provider has control over it.
    """

    domain = models.CharField(max_length=255)
    hash = models.CharField(max_length=255)
    provider = models.ForeignKey(
        "Hostingprovider",
        on_delete=models.CASCADE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )

    def clean(self):
        """
        Validate the domain using GreenDomainChecker.
        """

        # we have to import here to avoid a circular import
        from ...greencheck.domain_check import GreenDomainChecker

        checker = GreenDomainChecker()

        if not checker.validate_domain(self.domain):
            raise ValidationError({"domain": "Invalid domain provided"})

    def save(self, *args, **kwargs):
        """
        Generate a hash before saving.
        """
        if not self.hash:
            if not self.provider.shared_secret:
                raise NoSharedSecret

            self.hash = self.generate_hash()
        super().save(*args, **kwargs)

    def generate_hash(self) -> str:
        """
        Generates a SHA-256 hash based on the domain and the provider's shared secret.

        Returns:
            str: The generated hash in hexadecimal format.

        Raises:
            NoSharedSecret: If the provider does not have a shared secret.
        """
        """"""
        if not self.provider.shared_secret:
            raise NoSharedSecret

        hash_object = hashlib.sha256(
            f"{self.domain}{self.provider.shared_secret.body}".encode("utf-8")
        )
        # we want to be able to identify hashes by their issuer, so we prefix
        # it with a string denoting the issuer and the version of the algo used
        # to make the hash
        domain_hash_prefix = DOMAIN_HASH_ISSUER_ID
        return f"{domain_hash_prefix}-{hash_object.hexdigest()}"

    def __str__(self):
        return f"{self.domain} - {self.provider.name} - {self.hash[-8:]}"

    class Meta:
        db_table = "domain_hashes"


class Hostingprovider(models.Model):
    archived = models.BooleanField(default=False)
    country = CountryField(db_column="countrydomain")
    city = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="hostingproviders_created",
    )
    customer = models.BooleanField(default=False)
    icon = models.CharField(max_length=50, blank=True)
    iconurl = models.CharField(max_length=255, blank=True)
    model = EnumField(choices=ModelType.choices, default=ModelType.COMPENSATION)
    name = models.CharField(max_length=255, db_column="naam")
    description = models.TextField(blank=True, null=True)
    partner = models.CharField(
        max_length=255,
        null=True,
        default=PartnerChoice.NONE,
        choices=PartnerChoice.choices,
        blank=True,
    )
    service_tags = TaggableManager(
        verbose_name="Services Offered",
        help_text=(
            "Click the services that your organisation offers. These will be listed in"
            " the green web directory."
        ),
        blank=True,
    )
    services = TaggableManager(
        verbose_name="Services Offered",
        help_text=(
            "Click the services that your organisation offers. These will be listed in"
            " the green web directory."
        ),
        blank=True,
        through=ProviderService,
        # related_name="services",
    )
    # this should not be exposed publicly to end users.
    # It's for internal use
    staff_labels = TaggableManager(
        verbose_name="Staff labels",
        help_text=(
            "Labels to apply to providers to make it easier to flag for follow up "
            "by staff or other categorisation to support internal admin. "
            "Internally facing."
        ),
        through=ProviderLabel,
        blank=True,
        related_name="labels",
    )
    showonwebsite = models.BooleanField(verbose_name="Show on website", default=False)
    website = models.URLField(max_length=255)
    datacenter = models.ManyToManyField(
        "Datacenter",
        through="HostingproviderDatacenter",
        through_fields=("hostingprovider", "datacenter"),
        related_name="hostingproviders",
    )
    # link to a provider request that was recently used to create or update the data
    request = models.ForeignKey(
        # prevent circular imports by lazy-loading the ProviderRequest model
        "accounts.ProviderRequest",
        null=True,
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return self.name

    # Properties
    # TODO: we should try to move to only using properties for methods that
    # do not touch the database

    @property
    def users(self) -> models.QuerySet["User"]:
        """
        Returns a QuerySet of Users who have permissions for a given Hostingprovider
        """
        return get_users_with_perms(
            self, only_with_perms_in=(manage_provider.codename,)
        )

    @property
    def users_explicit_perms(self) -> models.QuerySet["User"]:
        """
        Returns a QuerySet of all Users that have *explicit* permissions to manage this Hostingprovider,
        not taking into consideration:
            - group membership
            - superuser status
        """
        return get_users_with_perms(
            self,
            only_with_perms_in=(manage_provider.codename,),
            with_superusers=False,
            with_group_users=False,
        )

    @property
    def is_awaiting_review(self):
        """
        Convenience check to see if this provider is labelled as
        awaiting a review by staff.
        """
        return AWAITING_REVIEW_SLUG in self.staff_labels.slugs()

    @property
    def admin_url(self) -> str:
        return reverse(
            "greenweb_admin:accounts_hostingprovider_change", args=[str(self.id)]
        )

    @property
    def shared_secret(self) -> str:
        try:
            return self.providersharedsecret
        except Hostingprovider.providersharedsecret.RelatedObjectDoesNotExist:
            raise NoSharedSecret

    @property
    def evidence_expiry_date(self) -> typing.Optional[datetime.date]:
        """
        Return the date of the most recent piece of supporting evidence
        for this provider. This would act as the effective expiry date
        for the listing.
        """
        most_recent_evidence = self.supporting_documents.all().order_by("-valid_to")

        if most_recent_evidence:
            return most_recent_evidence.first().valid_to

    @property
    def ip_range_count(self) -> int:
        """
        Convenience method for counting IP ranges.

        Used to when deciding how many to show on an admin page.
        """
        return self.greencheckip_set.all().count()

    @property
    def ip_approval_count(self) -> int:
        """
        Convenience method for counting IP approval requests.

        Used to when deciding how many to show on an admin page.
        """
        return self.greencheckipapprove_set.all().count()

    @property
    def website_domain(self) -> str:
        """Return the domain of the provider's website"""
        return urlparse(self.website_link).netloc

    @property
    def website_link(self) -> str:
        """
        Return a hyperlink for the website, accounting for whether
        the website link is stored as a fully qualified url or not
        """
        if self.website.startswith("http"):
            return self.website
        else:
            return f"https://{self.website}"

    # Mutators
    def refresh_shared_secret(self) -> str:
        try:
            existing_secret = self.providersharedsecret
            existing_secret.delete()
        except Hostingprovider.providersharedsecret.RelatedObjectDoesNotExist:
            pass

        rand_string = secrets.token_urlsafe(64)
        shared_secret = ProviderSharedSecret(
            body=f"GWF-{rand_string[4:]}", provider=self
        )
        shared_secret.save()

        return shared_secret.body

    def create_domain_hash(self, domain: str, user: "User") -> str:
        """
        Create a domain hash for the given provider using the latest shared secret.

        Args:
            domain (str): The domain to create a hash for.
            user (User): The user creating the hash.

        Returns:
            str: The generated domain hash.

        Raises:
            NoSharedSecret: If the provider does not have a shared secret.
            ValueError: If no user is associated with the provider.
            PermissionDenied: If the user does not have permission to update the provider.
        """
        if not user:
            raise ValueError(
                "A user must be associated with the provider to create a domain hash."
            )

        # check if the user has permission to update this provider

        if user not in self.users:
            raise PermissionDenied(
                "User does not have permission to update this provider"
            )

        if not self.shared_secret:
            raise NoSharedSecret

        # check for dupes so we won't end up with loads
        matching_provider_domains = self.domainhash_set.filter(domain=domain)
        domain_hash = DomainHash(domain=domain, provider=self, created_by=user)

        # we check for duplicates, based on the string value

        # TODO: look into making this a database constraint instead
        # i.e. unique on domain, provider, and shared secret in use.
        if matching_provider_domains:
            domain_hash.hash = domain_hash.generate_hash()
            for existing_hash in matching_provider_domains:
                if str(existing_hash) == str(domain_hash):
                    raise ValueError(
                        "Domain hash already exists for this domain and provider"
                    )

        domain_hash.clean()
        domain_hash.save()
        return domain_hash

    def label_as_awaiting_review(self, notify_admins=False):
        """
        Mark this hosting provider as in need of review by staff.
        Sends an notification email if the provider previously
        did not have this label.
        Returns None if we have a label already, otherwise returns
        the added label
        """

        # we already have the label, do nothing and return early
        if self.is_awaiting_review:
            return None

        # otherwise, we add the label
        self.staff_labels.add(AWAITING_REVIEW_STRING)

        if notify_admins:
            link_path = reverse(
                "greenweb_admin:accounts_hostingprovider_change", args=[self.id]
            )
            link_url = f"{settings.SITE_URL}{link_path}"

            email_text = render_to_string(
                "emails/provider-awaiting-review.txt",
                context={"provider": self.name, "link_url": link_url},
            )
            email_html = render_to_string(
                "emails/provider-awaiting-review.html",
                context={"provider": self.name, "link_url": link_url},
            )

            self.notify_admins(
                f"TGWF: {self.name} has been updated and is awaiting review",
                email_text,
                email_html,
            )
        return self.staff_labels.get(name=AWAITING_REVIEW_STRING)

    def mark_as_pending_review(self, approval_request):
        """
        Accept an IP / ASN approval request, and if the hosting provider
        doesn't already have outstanding approvals, notify admins
        to review the IP Range or AS network. Returns true if
        marking it as pending trigger action, otherwise false.
        """
        hosting_provider = approval_request.hostingprovider
        logger.debug(f"Approval request: {approval_request} for {hosting_provider}")

        if not self.is_awaiting_review:
            self.label_as_awaiting_review()
            self.request_network_review_from_admins(approval_request)
            return True

        return False

    def archive(self) -> "Hostingprovider":
        """
        Archive the provider, deactivating all the IP ranges
        and ASNs for this provider, removing it from listings
        """
        active_green_ips = self.greencheckip_set.filter(active=True)
        active_green_asns = self.greencheckasn_set.filter(active=True)
        active_green_ips.update(active=False)
        active_green_asns.update(active=False)

        self.archived = True
        self.showonwebsite = False
        self.save()
        return self

    # Queries

    def domain_hash_for_domain(self, domain: str) -> str:
        """
        Accept a domain, and return a hash of the domain and the
        shared secret for this provider.
        """
        if not self.shared_secret:
            raise NoSharedSecret

        hash_object = hashlib.sha256(
            f"{domain}{self.shared_secret.body}".encode("utf-8")
        )
        return hash_object.hexdigest()

    def public_supporting_evidence(
        self,
    ) -> models.QuerySet["HostingproviderSupportingDocument"]:
        """
        Return the supporting evidence that has explictly been marked as public
        by the users uploading it to the database
        """
        return self.supporting_documents.filter(public=True).order_by("-valid_to")

    def active_ip_ranges(self) -> models.QuerySet["GreencheckIP"]:
        """
        Return the active IP ranges for this provider
        """
        return self.greencheckip_set.filter(active=True)

    def active_asns(self) -> models.QuerySet["GreencheckASN"]:
        """
        Return the active ASNs for this provider
        """
        return self.greencheckasn_set.filter(active=True)

    def last_approved_verification_req(self) -> "ProviderRequest":
        return (
            self.providerrequest_set.filter(status="Approved")
            .order_by("-modified")
            .first()
        )

    def counts_as_green(self):
        """
        A convenience check, provide a simple to let us avoid
        needing to implement the logic for determining
        if a provider counts as green in multiple places
        """
        # TODO: this method should probably be a property
        return GREEN_VIA_CARBON_TXT in self.staff_labels.names()

    def outstanding_approval_requests(self):
        """
        Return all the ASN or IP Range requests as a single list.
        """
        logger.debug(self.greencheckasnapprove_set.all())
        logger.debug(self.greencheckipapprove_set.all())
        outstanding_asn_approval_reqs = self.greencheckasnapprove_set.filter(
            status__in=[StatusApproval.NEW, StatusApproval.UPDATE]
        )
        outstanding_ip_range_approval_reqs = self.greencheckipapprove_set.filter(
            status__in=[StatusApproval.NEW, StatusApproval.UPDATE]
        )
        # use list() to evalute the queryset to a datastructure that
        # we can concatenate easily
        approval_requests = list(outstanding_asn_approval_reqs) + list(
            outstanding_ip_range_approval_reqs
        )
        return approval_requests

    def notify_admins(self, subject: str, email_txt: str, email_html: str = None):
        """
        Send an email to the admins with the provided subject, email content.
        If an html version email_html is provided, the html variant is provided.
        """

        msg = AnymailMessage(
            subject=subject,
            body=email_txt,
            to=["support@thegreenwebfoundation.org"],
        )

        if email_html:
            msg.attach_alternative(email_html, "text/html")
        msg.send()

    def request_network_review_from_admins(self, approval_request):
        """
        Mark the approval request for this  hosting provider as
        in need of review by admins.
        Sends an notification via email to admins.
        """

        #  notify_admin_via_email(approval_request)
        link_path = reverse(
            "greenweb_admin:accounts_hostingprovider_change", args=[self.id]
        )
        link_url = f"{settings.SITE_URL}{link_path}"
        ctx = {
            "approval_request": approval_request,
            "provider": self,
            "link_url": link_url,
        }
        notification_subject = (
            f"TGWF: {self.name} - has been updated and needs a review"
        )

        notification_email_copy = render_to_string("flag_for_review_text.txt", ctx)
        notification_email_html = render_to_string("flag_for_review_text.html", ctx)

        self.notify_admins(
            notification_subject, notification_email_copy, notification_email_html
        )

    class Meta:
        # managed = False
        verbose_name = "Hosting Provider"
        db_table = "hostingproviders"
        indexes = [
            models.Index(fields=["name"], name="hp_name"),
            models.Index(fields=["archived"], name="hp_archived"),
            models.Index(fields=["showonwebsite"], name="hp_showonwebsite"),
        ]
        permissions = (manage_provider.astuple(),)


class ProviderSharedSecret(TimeStampedModel):
    """
    A shared secret linked to a provider. Used when
    checking if a domain hash has been generated from
    a provider's shared secret and given domain.
    """

    body = models.CharField(
        max_length=512,
        help_text="The body of the shared secret",
    )
    provider = models.OneToOneField(Hostingprovider, on_delete=models.CASCADE)


class AbstractNote(TimeStampedModel):
    """
    Notes around domain objects, to allow admin
    staff to add unstructured data, and links, and commentary
    add commentary or link to other information relating to
    """

    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True
    )
    body_text = models.TextField(blank=True)

    def __str__(self):
        added_at = self.created.strftime("%Y-%m-%d, %H:%M")
        return f"Note, added by {self.added_by} at {added_at}"

    class Meta:
        abstract = True


class SupportMessage(TimeStampedModel):
    """
    A model to represent the different kind of support messages we use when
    corresponding with providers and end users.
    """

    category = models.CharField(
        max_length=255,
        help_text="A category for this kind of message. For internal use",
    )
    subject = models.CharField(
        max_length=255,
        help_text=(
            "The default subject of the email message. This is what "
            "the user sees in their inbox"
        ),
    )
    body = models.TextField(
        help_text=(
            "The default content of the message sent to the user. Supports markdown."
        ),
    )

    def __str__(self):
        return self.category


class HostingProviderNote(AbstractNote):
    """
    A note model for information about a hosting provider.
    This is intended to be something internal staff use,
    but any content added should be considered as content
    you would be prepared to share with the provider as well.
    """

    provider = models.ForeignKey(Hostingprovider, null=True, on_delete=models.PROTECT)


class DatacenterNote(AbstractNote):
    """
    A note model for information about a datacentre - like the hosting note,
    but for annotating datacenters in the admin.
    """

    provider = models.ForeignKey(
        Datacenter, null=True, on_delete=models.PROTECT, db_column="id_dc"
    )


class DataCenterLocation(models.Model):
    """
    A join table linking datacentre cities
    to the country.
    """

    city = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    datacenter = models.ForeignKey(
        Datacenter, null=True, on_delete=models.CASCADE, db_column="id_dc"
    )

    def __str__(self):
        return f"{self.city}, {self.country}"

    class Meta:
        verbose_name = "Datacentre Location"
        db_table = "datacenters_locations"


class HostingCommunication(TimeStampedModel):
    template = models.CharField(max_length=128)
    hostingprovider = models.ForeignKey(
        Hostingprovider, null=True, on_delete=models.SET_NULL
    )
    # a store of the outbound messages we send, so we have a record
    # for future reference
    message_content = models.TextField(blank=True)


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


class EvidenceType(models.TextChoices):
    """
    Type of the supporting evidence, that certifies that green energy is used
    """

    ANNUAL_REPORT = "Annual report"
    WEB_PAGE = "Web page"
    CERTIFICATE = "Certificate"
    OTHER = "Other"


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
        help_text=(
            "If you have a sustainability report, or bill from a energy provider"
            " provider, or similar certificate of supply from a green tariff add it"
            " here."
        ),
    )
    url = models.URLField(
        blank=True,
        help_text=(
            "Alternatively, if you add a link, we'll fetch a copy at the URL you list,"
            " so we can point to the version when you listed it"
        ),
    )
    description = models.TextField(
        blank=True,
    )
    valid_from = models.DateField()
    valid_to = models.DateField()
    type = models.CharField(choices=EvidenceType.choices, max_length=255, null=True)
    public = models.BooleanField(
        default=True,
        help_text=(
            "If this is checked, we'll add a link to this "
            "document/page in your entry in the green web directory."
        ),
    )
    archived = models.BooleanField(
        default=False,
        editable=False,
        help_text=(
            "If this is checked, this document will not show up in any queries. "
            "Should not be editable via the admin interface by non-staff users."
        ),
    )

    def __str__(self):
        return f"{self.valid_from} - {self.title}"

    class Meta:
        abstract = True
        verbose_name = "Supporting Document"


class DatacenterSupportingDocument(AbstractSupportingDocument):
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


class NonArchivedEvidenceManager(models.Manager):
    """
    A custom manager to filter out archived items of supporting evidence
    for a given provider. Used as a default manager for
    Hosting Provider Supporting Documents, so we do not accidentally
    show archived evidence in queries.
    """

    def get_queryset(self) -> models.QuerySet:
        return super().get_queryset().filter(archived=False)


class HostingProviderSupportingDocument(AbstractSupportingDocument):
    """
    The subclass for hosting providers.
    """

    # our default manager should filter out archived items
    objects = NonArchivedEvidenceManager()
    # but we still should have access if neeed by via the
    # original non-filtered manager
    objects_all = models.Manager()

    hostingprovider = models.ForeignKey(
        Hostingprovider,
        db_column="id_hp",
        null=True,
        on_delete=models.CASCADE,
        related_name="supporting_documents",
    )

    def archive(self) -> "HostingProviderSupportingDocument":
        self.archived = True
        self.save()
        # TODO if we are using object storage, use the boto3 API to mark the
        # file as no longer public

        return self

    def unarchive(self) -> "HostingProviderSupportingDocument":
        self.archived = False
        self.save()
        # TODO if we are using object storage, use the boto3 API to mark the
        # file as no longer public

        return self

    @property
    def parent(self):
        return self.hostingprovider

    @property
    def link(self) -> str:
        """
        Return either the hyperlink to the attachment url, or the plain url.
        If an item has both, we assume the attachment takes priority.
        """

        # NOTE this shouldn't trigger any more db queries, so it
        # ought to be okay as a property. We probably should
        # change if it does trigger them.
        if self.attachment:
            return self.attachment.url

        return self.url


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

    def legacy_representation(self):
        """
        Return the JSON representation
        """
        return {
            "cert_valid_from": self.valid_from,
            "cert_valid_to": self.valid_to,
            "cert_url": self.url,
        }

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
    hostingprovider = models.OneToOneField(
        Hostingprovider,
        on_delete=models.CASCADE,
        db_column="id_hp",
        # this column is the foreign key for hosting providers
        # AND considered the primary key. Without this extra keyword,
        # we get crashes when deleting hosting providers
        primary_key=True,
    )
    green_domains = models.IntegerField()
    green_checks = models.IntegerField()

    class Meta:
        db_table = "hostingproviders_stats"
        # managed = False
