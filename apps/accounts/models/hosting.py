
from django.db import models
from django_countries.fields import CountryField
from django.contrib.auth.models import User
from django_mysql.models import EnumField

from .choices import EnergyType, TempType, ModelType


class Datacenter(models.Model):
    country = CountryField(db_column='countrydomain')
    dc12v = models.BooleanField()
    greengrid = models.BooleanField()
    mja3 = models.BooleanField(
        null=True,
        verbose_name='meerjaren plan energie 3'
    )
    model = models.CharField(max_length=255)
    name = models.CharField(max_length=255, db_column='naam')
    pue = models.FloatField(verbose_name='Power usage effectiveness')
    residualheat = models.BooleanField(null=True)
    showonwebsite = models.BooleanField()
    temperature = models.IntegerField(null=True)
    temperature_type = models.CharField(max_length=255, choices=TempType.choices)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    virtual = models.BooleanField()
    website = models.CharField(max_length=255)

    class Meta:
        db_table = 'datacenters'
        # managed = False


class DatacenterClassification(models.Model):
    # TODO if this is used to some extent, this should be m2m
    classification = models.CharField(max_length=255)
    datacenter = models.ForeignKey(
        Datacenter, db_column='id_dc', on_delete=models.CASCADE
    )


class DatacenterCooling(models.Model):
    # TODO if this is used to some extent, this should be m2m
    cooling = models.CharField(max_length=255)
    datacenter = models.ForeignKey(
        Datacenter, db_column='id_dc', on_delete=models.CASCADE
    )


class Hostingprovider(models.Model):
    archived = models.BooleanField()
    country = CountryField(db_column='countrydomain')
    customer = models.BooleanField()
    icon = models.CharField(max_length=50)
    iconurl = models.CharField(max_length=255)
    model = EnumField(
        choices=ModelType.choices, default=ModelType.compensation
    )
    name = models.CharField(max_length=255, db_column='naam')
    partner = models.CharField(max_length=255, null=True)
    showonwebsite = models.BooleanField()
    website = models.CharField(max_length=255)
    datacenter = models.ManyToManyField(
        'Datacenter',
        through='HostingproviderDatacenter',
        through_fields=('hostingprovider', 'datacenter')
    )

    class Meta:
        # managed = False
        db_table = 'hostingproviders'
        indexes = [
            models.Index(fields=['archived']),
            models.Index(fields=['showonwebsite']),
        ]


class HostingproviderDatacenter(models.Model):
    '''Intermediary table between Datacenter and Hostingprovider'''
    approved = models.BooleanField()
    approved_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    datacenter = models.ForeignKey(Datacenter, null=True, on_delete=models.CASCADE)
    hostingprovider = models.ForeignKey(
        Hostingprovider, null=True, on_delete=models.CASCADE
    )

    class Meta:
        db_table = 'datacenters_hostingproviders'
        # managed = False


class Certificate(models.Model):
    energyprovider = models.CharField(max_length=255)
    mainenergy_type = models.CharField(
        max_length=255, db_column='mainenergytype', choices=EnergyType.choices
    )
    url = models.CharField(max_length=255)
    valid_from = models.DateField()
    valid_to = models.DateField()

    class Meta:
        abstract = True


class DatacenterCertificate(Certificate):
    datacenter = models.ForeignKey(
        Datacenter, db_column='id_dc', null=True, on_delete=models.CASCADE
    )

    class Meta:
        db_table = 'datacenter_certificates'
        # managed = False


class HostingproviderCertificate(Certificate):
    hostingprovider = models.ForeignKey(
        Datacenter, db_column='id_hp', null=True, on_delete=models.CASCADE
    )

    class Meta:
        db_table = 'hostingprovider_certificates'
        # managed = False


class HostingproviderStats(models.Model):
    hostingprovider = models.ForeignKey(Hostingprovider, on_delete=models.CASCADE)
    green_domains = models.IntegerField()
    green_checks = models.IntegerField()

    class Meta:
        db_table = 'hostingproviders_stats'
        # managed = False

