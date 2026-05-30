from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from taggit import models as tag_models
from model_utils.models import TimeStampedModel
from ..choices import EnergyType

class Label(tag_models.TagBase):
    """
    The base tag class we need in order to create a separate set of
    tags to use as internal labels
    """

    class Meta:
        verbose_name = _("Label")
        verbose_name_plural = _("Labels")


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


