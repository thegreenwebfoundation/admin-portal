import logging  # noqa
from datetime import date, datetime, timedelta
from typing import Iterable, List, Tuple, Union

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from django_countries.fields import CountryField
from guardian.shortcuts import assign_perm
from model_utils.models import TimeStampedModel
from taggit import models as tag_models
from taggit.managers import TaggableManager

from apps.accounts.permissions import manage_provider
from apps.greencheck.models import GreencheckASN, GreencheckIp, IpAddressField
from apps.greencheck.validators import validate_ip_range

from .hosting import (
    EvidenceType,
    Hostingprovider,
    HostingProviderSupportingDocument,
    Service,
)

import ipaddress

logger = logging.getLogger(__name__)  # noqa


class ProviderRequestStatus(models.TextChoices):
    """
    Status of the ProviderRequest, exposed to both: end users and staff.
    Some status change (PENDING_REVIEW -> ACCEPTED) will be later used to trigger
    automatic creation of the different resources in the system.

    Meaning of each value:
    - PENDING_REVIEW: GWF staff needs to verify the request
    - APPROVED: GWF staff approved the request
    - REJECTED: GWF staff rejected the request (completely)
    - OPEN: GWF staff requested some changes from the provider
    - REMOVED: This request was not rejected, should no longer be shown to the user.
    """

    PENDING_REVIEW = "Pending review"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    OPEN = "More info required"
    REMOVED = "Removed"


class ProviderRequestService(tag_models.TaggedItemBase):
    """
    The corresponding through model for linking a Provider to
    a Service as outlined above.
    """

    content_object = models.ForeignKey(
        "ProviderRequest",
        on_delete=models.CASCADE,
    )
    tag = models.ForeignKey(
        Service,
        related_name="%(app_label)s_%(class)s_items",
        on_delete=models.CASCADE,
    )


class VerificationBasis(tag_models.TagBase):
    """
    A model representing reasons why a provider would be verified.
    This includes things like

        "We use 100% green energy from our own infrastructure.",
        "We operate in a region that has a grid intensity of less than 20g CO2e/kWh or uses over 99% renewable power.",
        "We directly pay for green energy to cover the non-green energy we use.",
        "We purchase quality carbon offsets to cover the non-green energy we use.",
        "We resell or actively use a provider that is already in the Green Web Dataset.",

    A subclass of Taggit's 'TagBase' model.

    """


    # Annoyingly, the only way to override the max_length in taggit appears to be to copy and adjust
    # these two field definitions wholesale: https://github.com/jazzband/django-taggit/issues/510
    name = models.CharField(
        verbose_name=pgettext_lazy("A tag name", "name"), unique=True, max_length=255
    )

    slug = models.SlugField(
        verbose_name=pgettext_lazy("A tag slug", "slug"),
        unique=True,
        max_length=255,
        allow_unicode=True,
    )

    class Meta:
        verbose_name = _("Basis for verification")
        verbose_name_plural = _("Bases for verification")


class ProviderRequestVerificationBasis(tag_models.TaggedItemBase):
    """
    The corresponding through model for linking a Provider to
    a VerificationBasis as outlined above.
    """

    content_object = models.ForeignKey(
        "ProviderRequest",
        on_delete=models.CASCADE,
    )
    tag = models.ForeignKey(
        VerificationBasis,
        related_name="%(app_label)s_%(class)s_items",
        on_delete=models.CASCADE,
    )


class ProviderRequest(TimeStampedModel):
    """
    Model representing the input data
    as submitted by the provider to our system,
    when they want to include their information into our dataset --
    also known as verification request.

    """

    name = models.CharField(max_length=255)
    website = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(
        choices=ProviderRequestStatus.choices,
        max_length=255,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True
    )
    approved_at = models.DateTimeField(editable=False, blank=True, null=True)
    authorised_by_org = models.BooleanField()
    services = TaggableManager(
        verbose_name="Services offered",
        help_text=(
            "Click the services that your organisation offers. These will be listed in"
            " the green web directory."
        ),
        blank=True,
        through=ProviderRequestService,
    )
    verification_bases = TaggableManager(
        verbose_name="Basis for verification",
        blank=True,
        through=ProviderRequestVerificationBasis,
    )
    missing_network_explanation = models.TextField(
        verbose_name="Reason for no IP / AS data",
        help_text=(
            "If an organisation is not listing IP Ranges and AS numbers, "
            "we need a way to identify them in network lookups."
        ),
        blank=True,
    )
    location_import_required = models.BooleanField(default=False)
    network_import_required = models.BooleanField(default=False)
    data_processing_opt_in = models.BooleanField(
        default=False, verbose_name="Data processing consent"
    )
    newsletter_opt_in = models.BooleanField(
        default=False, verbose_name="Newsletter signup"
    )
    # if this field is set, approving a request will update the provider instead of creating a new one
    provider = models.ForeignKey(
        to=Hostingprovider, on_delete=models.SET_NULL, null=True
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
        services = Service.objects.filter(slug__in=service_slugs)
        self.services.set(services)

    def set_verification_bases_from_slugs(self, verification_basis_slugs: Iterable[str]) -> None:
        """
        Given list of verification_basis slugs (corresponding to Tag slugs)
        apply matching verification_bases to the ProviderRequest object
        """
        verification_bases = VerificationBasis.objects.filter(slug__in=verification_basis_slugs)
        self.verification_bases.set(verification_bases)

    @classmethod
    def get_service_choices(cls) -> List[Tuple[int, str]]:
        """
        Returns a list of available services (implemented in the Tag model)
        in a format expected by ChoiceField
        """
        return [(tag.slug, tag.name) for tag in Service.objects.all()]

    @classmethod
    def get_verification_bases_choices(cls) -> List[Tuple[int, str]]:
        """
        Returns a list of available verification bases (implemented in the Tag model)
        in a format expected by ChoiceField
        """
        return [(tag.slug, tag.name) for tag in VerificationBasis.objects.all()]

    @transaction.atomic
    def approve(self) -> Hostingprovider:
        """
        Create a new Hostingprovider and underlying objects or update an existing one
        and set appropriate permissions.
        When a Hostingprovider is being updated, information that was associated with them
        before, but is no longer present in the verification request, will be archived.
        This means it will not show up in the admin or on the provider.

        This method is defined as an atomic transaction:
        in case any exception occurs, all changes will be rolled back,
        allowing to keep a consistent database state.

        Please note that the rolled back transactions *do not reset*
        the state of models - to reflect the correct state,
        models need to be retrieved from the database again.
        See more details here:
        https://docs.djangoproject.com/en/4.1/topics/db/transactions/#controlling-transactions-explicitly
        """
        failed_msg = f"Failed to approve the request '{self}'"

        # Fail when request is already approved
        if self.status == ProviderRequestStatus.APPROVED:
            raise ValueError(f"{failed_msg} because it's already marked as approved")

        # Fail when a related Hostingprovider object already exists
        existing_hp = Hostingprovider.objects.filter(request=self)
        if existing_hp.exists():
            raise ValueError(
                f"{failed_msg} an existing hosting provider '{existing_hp.get()}'"
                "was already updated using the data from this verification request"
            )

        # Temporarily use only the first location
        # TODO: change this once Hostingprovider model has multiple locations attached
        first_location = self.providerrequestlocation_set.first()
        if not first_location:
            raise ValueError(f"{failed_msg} because there are no locations provided")

        # decide whether to update an existing provider or create a new one
        if self.provider:
            hp = Hostingprovider.objects.get(pk=self.provider.id)

            # delete related objects, they will be recreated with recent data
            hp.services.clear()

            # TODO: we currently do not log any changes to a
            # provider in django admin if their IPs, ASNs or evidence have changed
            # as a result of this approval workflow.
            # We had this in the django admin and it
            # was very handy.
            # We need to make a decision about whether we want to log these
            # changes here or not.
            for asn in hp.greencheckasn_set.all():
                asn.archive()

            for ip_range in hp.greencheckip_set.all():
                ip_range.archive()

            for doc in hp.supporting_documents.all():
                doc.archive()

        else:
            hp = Hostingprovider.objects.create()
            self.provider = hp

        # fill in data from this request
        hp.name = self.name
        hp.description = self.description
        # set the first location from the list
        hp.country = first_location.country
        hp.city = first_location.city
        hp.website = self.website
        hp.request = self
        hp.created_by = self.created_by

        # if we have approved a submission from a provider
        hp.archived = False

        # set services (https://django-taggit.readthedocs.io/en/latest/api.html)
        hp.services.set(list(self.services.all()))
        hp.staff_labels.add("up-to-date")

        # we use the tag with the slug "other-none" for
        # organisations that we would need to recognise as
        # using green energy, but who do not offer hosted services
        if "other-none" in hp.services.slugs():
            hp.showonwebsite = False
        else:
            hp.showonwebsite = True

        hp.save()

        # set permissions
        assign_perm(manage_provider.codename, self.created_by, hp)

        # (re)create related objects: ASNs
        for asn in self.providerrequestasn_set.all():
            # check if this asn was one we just archived, and make it visible
            # if so
            if matching_inactive_asn := GreencheckASN.objects.filter(
                active=False, asn=asn.asn, hostingprovider=hp
            ):
                [inactive_asn.unarchive() for inactive_asn in matching_inactive_asn]
                continue
            try:
                GreencheckASN.objects.create(
                    active=True, asn=asn.asn, hostingprovider=hp
                )
            except IntegrityError as e:
                raise ValueError(
                    f"Failed to approve the request `{self}` because the ASN '{asn}' already exists in the database"
                ) from e

        # (re)create related objects: new IP ranges
        for ip_range in self.providerrequestiprange_set.all():
            # check inactive matching IP ranges exist in the database
            # and mark them as active is so
            if matching_inactive_ip := GreencheckIp.objects.filter(
                active=False,
                ip_start=ip_range.start,
                ip_end=ip_range.end,
                hostingprovider=hp,
            ):
                [inactive_ip.unarchive() for inactive_ip in matching_inactive_ip]
                continue

            GreencheckIp.objects.create(
                active=True,
                ip_start=ip_range.start,
                ip_end=ip_range.end,
                hostingprovider=hp,
            )

        # Fetch our archived documents:
        # We want to compare the submitted evidence against these
        # so we know which ones to make visible again, and which
        # ones to leave archived
        archived_documents = HostingProviderSupportingDocument.objects_all.filter(
            archived=True, hostingprovider=hp
        )
        archived_doc_ids = []

        def is_already_uploaded(evidence: ProviderRequestEvidence) -> Union[int, None]:
            """
            Check if the evidence is a content match for any of the archived documents
            returning the if of the match if so
            """
            for doc in archived_documents:
                logger.debug(evidence)
                logger.debug(doc)
                if evidence.has_content_match(doc):
                    return doc.id
            return None

        # create related objects: supporting documents
        for evidence in self.providerrequestevidence_set.all():
            logger.debug(f"checking for matching evidence for: {evidence}")

            # AbstractSupportingDocument does not accept null values for `url`
            # and `attachment` fields
            url = evidence.link or ""
            attachment = evidence.file or ""

            if archived_document_match := is_already_uploaded(evidence):
                logger.debug(
                    (
                        f"Marking evidence: {evidence} to be unarchived, because "
                        f"it is a match for doc id: {archived_document_match}"
                    )
                )
                archived_doc_ids.append(archived_document_match)

                # exit the loop early - this was a duplicate of content
                # that will be made visible again when we unarchive it,
                # so we don't need to create a new document
                continue

            supporting_doc = HostingProviderSupportingDocument.objects.create(
                hostingprovider=hp,
                title=evidence.title,
                attachment=attachment,
                url=url,
                description=evidence.description,
                # evidence is valid for 1 year from the time the request is approved
                valid_from=date.today(),
                valid_to=date.today() + timedelta(days=365),
                type=evidence.type,
                public=evidence.public,
            )
            logger.debug(
                f"Created supporting doc: {supporting_doc} for evidence: {evidence}"
            )

        # At this point we have created new supporting documents for evidence we
        # haven't seen before.
        # We now want to restore the visibility of archived documents that were content
        # matches for submitted evidence, by unarchiving them.
        [
            doc.unarchive()
            for doc in HostingProviderSupportingDocument.objects_all.filter(
                id__in=archived_doc_ids
            )
        ]

        # change status of the request
        self.status = ProviderRequestStatus.APPROVED
        self.approved_at = datetime.now()
        self.save()

        return hp


class ProviderRequestLocation(models.Model):
    """
    Each ProviderRequest may be connected to many ProviderRequestLocations,
    in which the new provider offers services.
    """

    name = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=255)
    country = CountryField()
    request = models.ForeignKey(ProviderRequest, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.request.name} | { self.name } {self.country.name}/{self.city}"


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

    def ip_range_size(self) -> int:
        """
        Return the size of the IP range, based on the start and end ip address.
        """
        if not self.start or not self.end:
            return 0

        # Convert string IP addresses to IP address objects
        start_ip = ipaddress.ip_address(self.start)
        end_ip = ipaddress.ip_address(self.end)

        # Calculate the difference and add 1 (if start and end IP addresses are the same, we still want it to show as 1)
        return int(end_ip) - int(start_ip) + 1

    # Add a short description for the admin
    ip_range_size.short_description = "IP Range Size"

    def clean(self) -> None:
        """
        Validates an IP range.

        Checking if values are not falsy is a workaround
        for a surprising ModelForm implementation detail:

        ModelForm connected to this Model executes Model.full_clean
        with "None" values in case the values were considered invalid
        according to the ModelForm validation logic.
        """
        if self.start and self.end:
            try:
                validate_ip_range(self.start, self.end)
            except ValueError as e:
                raise ValidationError({"start": e})
            except TypeError as e:
                raise ValidationError({"Mismatching IP ranges": e})


class ProviderRequestEvidence(models.Model):
    """
    Document that certifies that green energy is used by the provider.
    A single evidence is either a web link or a file.
    """

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    link = models.URLField(null=True, blank=True)
    file = models.FileField(null=True, blank=True, upload_to="uploads/")
    type = models.CharField(choices=EvidenceType.choices, max_length=255)
    public = models.BooleanField(default=False)
    request = models.ForeignKey(ProviderRequest, on_delete=models.CASCADE)

    def __str__(self) -> str:
        name = self.link or self.file.name
        long_name = f"{name}: {self.title}"
        if self.public:
            return f"{long_name} (public)"
        return f"{long_name} (private)"

    def clean(self) -> None:
        reason = "Provide a link OR a file for this evidence"
        if self.link is None and not bool(self.file):
            raise ValidationError(f"{reason}, you haven't submitted either.")
        if self.link and bool(self.file):
            raise ValidationError(f"{reason}, you've attempted to submit both.")

    def has_content_match(self, other_doc: "HostingProviderSupportingDocument") -> bool:
        """
        Check if an evidence is functionally equivalent to an existing supporting document.

        Two pieces of evidence are considered equivalent if they have the same
        title, type, and public status, link or attachment content
        """
        content_match = False

        if self.file and other_doc.attachment:
            self.file.seek(0)
            file_contents = self.file.read()
            other_doc.attachment.seek(0)
            other_doc_contents = other_doc.attachment.read()
            content_match = file_contents == other_doc_contents

        if self.link and other_doc.url:
            content_match = self.link == other_doc.url

        return (
            self.title == other_doc.title
            and self.type == other_doc.type
            and self.public == other_doc.public
            and content_match
        )
