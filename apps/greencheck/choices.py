from django.db import models
from django.utils.translation import gettext_lazy as _


class GreenlistChoice(models.TextChoices):
    """
    Choices for describing how a green check has arrived at
    its result.
    """

    ASN = "as", _("as")
    IP = "ip", _("ip")
    NONE = "none", _("none")
    URL = "url", _("url")
    WHOIS = "whois", _("whois")


class CheckedOptions(models.TextChoices):
    """
    Options for describing the source of the green check.
    What triggered the check?
    """

    ADMIN = "admin", _("admin")
    API = "api", _("api")
    APISEARCH = "apisearch", _("apisearch")
    BOTS = "bots", _("bots")
    TEST = "test", _("test")
    WEBSITE = "website", _("website")


class BoolChoice(models.TextChoices):
    """
    A stand in for our booleans. Legacy from the
    earlier app.
    """

    YES = "yes"
    NO = "no"
    OLD = "old"


class StatusApproval(models.TextChoices):
    APPROVED = "approved", _("Approved")
    DELETED = "deleted", _("Deleted")
    NEW = "new", _("New")
    REMOVED = "removed", _("Removed")
    UPDATE = "update", _("Update")


class ActionChoice(models.TextChoices):
    EMPTY = "empty", _("empty")
    NEW = "new", _("new")
    UPDATE = "update", _("update")
    NONE = "none", _("none")


class DailyStateChoices(models.TextChoices):
    DAILY_TOTAL = "total_daily_checks", _("Total daily checks")
