from django.db import models, IntegrityError, transaction
from django.urls import reverse
from django.conf import settings
from django.core.exceptions import ValidationError

from django_countries.fields import CountryField
from taggit.managers import TaggableManager
from taggit import models as tag_models
from datetime import date, timedelta, datetime
from guardian.shortcuts import assign_perm


from apps.greencheck.models import IpAddressField, GreencheckASN, GreencheckIp
from apps.greencheck.validators import validate_ip_range
from apps.accounts.permissions import manage_provider
from model_utils.models import TimeStampedModel
from typing import Iterable, Tuple, List
from .hosting import (
    Hostingprovider,
    HostingProviderSupportingDocument,
    EvidenceType,
    Service,
)


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

    @classmethod
    def get_service_choices(cls) -> List[Tuple[int, str]]:
        """
        Returns a list of available services (implemented in the Tag model)
        in a format expected by ChoiceField
        """
        return [(tag.slug, tag.name) for tag in Service.objects.all()]

    @transaction.atomic
    def approve(self) -> Hostingprovider:
        """
        Create a new Hostingprovider and underlying objects or update an existing one
        and set appropriate permissions.

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

            for asn in hp.greencheckasn_set.all():
                asn.delete()

            for ip_range in hp.greencheckip_set.all():
                ip_range.delete()

            for doc in hp.supporting_documents.all():
                doc.delete()

        else:
            hp = Hostingprovider.objects.crete()
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

        # create related objects: ASNs
        for asn in self.providerrequestasn_set.all():
            try:
                GreencheckASN.objects.create(
                    active=True, asn=asn.asn, hostingprovider=hp
                )
            except IntegrityError as e:
                raise ValueError(
                    f"Failed to approve the request `{self}` because the ASN '{asn}' already exists in the database"
                ) from e

        # create related objects: IP ranges
        for ip_range in self.providerrequestiprange_set.all():
            GreencheckIp.objects.create(
                active=True,
                ip_start=ip_range.start,
                ip_end=ip_range.end,
                hostingprovider=hp,
            )

        # create related objects: supporting documents
        for evidence in self.providerrequestevidence_set.all():
            # AbstractSupportingDocument does not accept null values for `url` and `attachment` fields
            url = evidence.link or ""
            attachment = evidence.file or ""
            HostingProviderSupportingDocument.objects.create(
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
            validate_ip_range(self.start, self.end)


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
