from django.conf import settings
from django.db import models
from django.urls import reverse
from django_countries.fields import CountryField
from guardian.shortcuts import get_users_with_perms
from ...permissions import manage_datacenter
from ..choices import (
    ClassificationChoice,
    CoolingChoice,
    ModelType,
    TempType
)
from .abstract import AbstractNote, AbstractSupportingDocument, Certificate

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

class DatacenterNote(AbstractNote):
    """
    A note model for information about a datacentre - like the hosting note,
    but for annotating datacenters in the admin.
    """

    provider = models.ForeignKey(
        Datacenter, null=True, on_delete=models.PROTECT, db_column="id_dc"
    )

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

