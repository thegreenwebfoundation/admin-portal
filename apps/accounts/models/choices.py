from django.db import models
from django.utils.translation import gettext_lazy as _


class EnergyType(models.TextChoices):
    WIND = "wind"
    WATER = "water"
    SOLAR = "solar"
    MIXED = "mixed"


class TempType(models.TextChoices):
    C = "C"
    F = "F"


class ModelType(models.TextChoices):
    GREEN_ENERGY = "groeneenergie"
    COMPENSATION = "compensatie"
    MIXED = "mixed"


class PartnerChoice(models.TextChoices):
    NONE = "None"
    PARTNER = "Partner"
    DEV_PARTNER = "Dev Partner"
    CERTIFIED_GOLD = "Certified Gold Partner"
    CERTIFIED_PARTNER = "Certified Partner"
    GOLD = "Gold Partner"


class ClassificationChoice(models.TextChoices):
    GREENGRID = "GreenGrid", _("GreenGrid")
    ENERGYSTART = "EnergyStart", _("EnergyStart")
    BREEAM = "BREEAM", _("BREEAM")
    LEED = "LEED", _("LEED")
    EPA = "EPA", _("EPA")


class CoolingChoice(models.TextChoices):
    DIRECT_FREE = "Direct free"
    COMPRESSOR = "Compressor"
    INDIRECT_FREE = "Indirect free"
    WATER = "Water"
    COLD_WHEEL = "Cold Wheel"
