import decimal
import ipaddress
import logging
import typing
from dataclasses import dataclass

from dateutil.relativedelta import relativedelta
from django import forms
from django.core import exceptions, validators
from django.db import models
from django.db.models.fields import Field
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.text import capfirst
from django_mysql import models as dj_mysql_models
from django_mysql import models as mysql_models
from model_utils import models as mu_models

from ...accounts import models as ac_models
from .. import choices as gc_choices

logger = logging.getLogger(__name__)
"""
- greencheck_linked - the purpose of the table is not very clear.
   Contains many entries though.
- greencheck_stats_total and greencheck_stats - self explanatory.
   See https://admin.thegreenwebfoundation.org/admin/stats/greencheck

# wait for reply on these.
- greenenergy - also an old table
"""


now = timezone.now()
yesterday = now - relativedelta(days=1)


@dataclass
class SiteCheck:
    """
    A representation of the Sitecheck object from the PHP app.
    We use it as a basis for logging to the Greencheck, but also maintaining
    our green_domains tables.
    """

    url: str
    ip: str
    data: bool
    green: bool
    hosting_provider_id: int
    checked_at: str
    match_type: str
    match_ip_range: int
    cached: bool


class IpAddressField(Field):
    default_error_messages = {
        "invalid": "'%(value)s' value must be a valid IpAddress.",
    }
    description = "IpAddress"
    empty_strings_allowed = False

    def __init__(self, *args, **kwargs):
        kwargs.pop("max_digits", None)
        kwargs.pop("decimal_places", None)
        self.max_digits = 39
        self.decimal_places = 0
        super().__init__(*args, **kwargs)
        self.validators = []

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        return errors

    @cached_property
    def validators(self):
        return super().validators + [
            validators.DecimalValidator(self.max_digits, self.decimal_places)
        ]

    @cached_property
    def context(self):
        return decimal.Context(prec=self.max_digits)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.max_digits is not None:
            kwargs["max_digits"] = self.max_digits
        if self.decimal_places is not None:
            kwargs["decimal_places"] = self.decimal_places
        return name, path, args, kwargs

    def to_python(self, value):
        if value is None:
            return value
        try:
            if hasattr(value, "quantize"):
                return ipaddress.ip_address(int(value))
            return ipaddress.ip_address(value)
        except (TypeError, ValueError):
            raise exceptions.ValidationError(
                self.error_messages["invalid"], code="invalid", params={"value": value},
            )

    def get_db_prep_save(self, value, connection):
        value = self.get_prep_value(value)
        return connection.ops.adapt_decimalfield_value(
            value, self.max_digits, self.decimal_places
        )

    def get_prep_value(self, value):
        if value is not None:
            if isinstance(value, str):
                value = ipaddress.ip_address(value)

            return decimal.Decimal(int(value))
        return None

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return str(ipaddress.ip_address(int(value)))

    def get_internal_type(self):
        return "DecimalField"

    def formfield(self, form_class=None, choices_form_class=None, **kwargs):
        """Return a django.forms.Field instance for this field."""
        defaults = {
            "required": not self.blank,
            "label": capfirst(self.verbose_name),
            "help_text": self.help_text,
        }
        if self.has_default():
            if callable(self.default):
                defaults["initial"] = self.default
                defaults["show_hidden_initial"] = True
            else:
                defaults["initial"] = self.get_default()
        defaults.update(kwargs)
        if form_class is None:
            form_class = forms.CharField
        return form_class(**defaults)


class GreencheckIp(mu_models.TimeStampedModel):
    """
    An IP Range associated with a hosting provider, to act as a way to
    link it to the sustainability claims by the company.
    """

    active = models.BooleanField(null=True)
    ip_end = IpAddressField(db_column="ip_eind")
    ip_start = IpAddressField()
    hostingprovider = models.ForeignKey(
        ac_models.Hostingprovider, db_column="id_hp", on_delete=models.CASCADE
    )

    def ip_range_length(self) -> int:
        """
        Return the length of the ip range beginning at
        ip_start, and ending at ip_end
        """
        return (
            int(ipaddress.IPv4Address(self.ip_end))
            - int(ipaddress.IPv4Address(self.ip_start))
            + 1
        )
        # return len(ip_range)

    def __str__(self):
        return f"{self.ip_start} - {self.ip_end}"

    class Meta:
        db_table = "greencheck_ip"
        indexes = [
            models.Index(fields=["ip_end"], name="ip_eind"),
            models.Index(fields=["ip_start"], name="ip_start"),
            models.Index(fields=["active"], name="active"),
        ]


class Greencheck(mysql_models.Model):
    # NOTE: ideally we would have these two as Foreign keys, as the greencheck
    # table links back to where the recorded ip ranges we checked against are.
    # However, some `GreencheckIP` ip range objects have been deleted over
    # the years.
    # Also,
    # We might be better off with a special 'DELETED' Greencheck IP
    # to at least track this properly.
    hostingprovider = models.IntegerField(db_column="id_hp", default=0)
    # hostingprovider = models.ForeignKey(
    #     ac_models.Hostingprovider,
    #     db_column="id_hp",
    #     on_delete=models.CASCADE,
    #     blank=True,
    #     null=True,
    # )
    greencheck_ip = models.IntegerField(db_column="id_greencheck", default=0)
    # greencheck_ip = models.ForeignKey(
    #     GreencheckIp,
    #     on_delete=models.CASCADE,
    #     db_column="id_greencheck",
    #     blank=True,
    #     null=True,
    # )
    date = models.DateTimeField(db_column="datum")
    green = dj_mysql_models.EnumField(choices=gc_choices.BoolChoice.choices)
    ip = IpAddressField()
    tld = models.CharField(max_length=64)
    type = dj_mysql_models.EnumField(
        choices=gc_choices.GreenlistChoice.choices,
        default=gc_choices.GreenlistChoice.NONE,
    )

    url = models.CharField(max_length=255)

    class Meta:
        db_table = "greencheck_2021"

    def __str__(self):
        return f"{self.url} - {self.ip}"


class GreencheckIpApprove(mu_models.TimeStampedModel):
    """
    An approval request for a given IP Range. These are submitted by hosting providers
    and once they are reviewed, and approved, a new IP Range with the same IP addresses
    is created.
    """

    action = models.TextField(choices=gc_choices.ActionChoice.choices)
    hostingprovider = models.ForeignKey(
        ac_models.Hostingprovider,
        on_delete=models.CASCADE,
        db_column="id_hp",
        null=True,
    )
    greencheck_ip = models.ForeignKey(
        GreencheckIp, on_delete=models.CASCADE, db_column="idorig", null=True
    )
    ip_end = IpAddressField(db_column="ip_eind")
    ip_start = IpAddressField()
    status = models.TextField(choices=gc_choices.StatusApproval.choices)

    # Factories
    def process_approval(self, action):
        """
        Accept an action, and if the action was one of approval
        return the created Green Ip range, corresponding to this
        Green Ip approval request.
        """
        self.status = action
        created_ip_range = None

        if action == gc_choices.StatusApproval.APPROVED:
            created_ip_range = GreencheckIp.objects.create(
                active=True,
                hostingprovider=self.hostingprovider,
                ip_start=self.ip_start,
                ip_end=self.ip_end,
            )
            self.greencheck_ip = created_ip_range

            # some IP approvals historically do not
            # have a 'created' value, so we add
            # something here. Without
            # it, the database won't let us save the changes
            if not self.created:
                self.created = timezone.now()

        self.save()
        if created_ip_range:
            return created_ip_range

    # Mutators
    # Queries
    # Properties

    def __str__(self):
        return f"{self.ip_start} - {self.ip_end}: {self.status}"

    class Meta:
        db_table = "greencheck_ip_approve"
        verbose_name = "Greencheck IP Range Submission"
        # managed = False


class GreencheckLinked(models.Model):
    # waiting for use case first...
    pass


class GreenList(models.Model):
    greencheck = models.ForeignKey(
        Greencheck, on_delete=models.CASCADE, db_column="id_greencheck"
    )
    hostingprovider = models.ForeignKey(
        ac_models.Hostingprovider, on_delete=models.CASCADE, db_column="id_hp"
    )
    last_checked = models.DateTimeField()
    name = models.CharField(max_length=255, db_column="naam")
    type = dj_mysql_models.EnumField(choices=gc_choices.ActionChoice.choices)
    url = models.CharField(max_length=255)
    website = models.CharField(max_length=255)

    class Meta:
        # managed = False
        db_table = "greenlist"
        indexes = [
            models.Index(fields=["url"], name="url"),
        ]


class GreencheckTLD(models.Model):
    checked_domains = models.IntegerField()
    green_domains = models.IntegerField()
    hps = models.IntegerField(verbose_name="Hostingproviders registered in tld")
    tld = models.CharField(max_length=50)
    toplevel = models.CharField(max_length=64)

    class Meta:
        db_table = "greencheck_tld"
        indexes = [
            models.Index(fields=["tld"], name="tld"),
        ]


class GreencheckASN(mu_models.TimeStampedModel):
    """
    An AS Number to identify a hosting provider with, so we can link
    an IP address or ASN to the hosting provider's green claims.
    """

    active = models.BooleanField(null=True)
    # https://en.wikipedia.org/wiki/Autonomous_system_(Internet)
    asn = models.IntegerField(verbose_name="Autonomous system number")
    hostingprovider = models.ForeignKey(
        ac_models.Hostingprovider, on_delete=models.CASCADE, db_column="id_hp"
    )

    class Meta:
        db_table = "greencheck_as"
        indexes = [
            models.Index(fields=["active"], name="as_active"),
            models.Index(fields=["asn"], name="as_asn"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["asn", "active"], name="unique_active_asns"
            ),
        ]


class GreencheckASNapprove(mu_models.TimeStampedModel):
    """
    A greencheck ASN approve is a request, to register an AS Network
    with a given hosting provider. Once approved, associates the AS
    with the provider.
    """

    action = models.TextField(choices=gc_choices.ActionChoice.choices)
    asn = models.IntegerField()
    hostingprovider = models.ForeignKey(
        ac_models.Hostingprovider, on_delete=models.CASCADE, db_column="id_hp"
    )
    greencheck_asn = models.ForeignKey(
        GreencheckASN, on_delete=models.CASCADE, db_column="idorig", null=True
    )
    status = models.TextField(choices=gc_choices.StatusApproval.choices)

    def process_approval(self, action):
        """
        Accept an action, and if the action was one of approval
        return the created the GreenASN, corresponding to this
        approval request
        """
        self.status = action
        created_asn = None

        if action == gc_choices.StatusApproval.APPROVED:
            created_asn = GreencheckASN.objects.create(
                active=True, hostingprovider=self.hostingprovider, asn=self.asn,
            )
            self.greencheck_asn = created_asn
        self.save()
        if created_asn:
            return created_asn

    def __str__(self):
        return f"ASN: {self.asn} - Status: {self.status} Action: {self.action}"

    class Meta:
        db_table = "greencheck_as_approve"
        verbose_name = "Greencheck ASN Submissions"


class TopUrl(models.Model):
    url = models.CharField(max_length=255)

    class Meta:
        db_table = "top_1m_urls"


class GreenDomain(models.Model):

    url = models.CharField(max_length=255)
    hosted_by_id = models.IntegerField()
    hosted_by = models.CharField(max_length=255)
    hosted_by_website = models.CharField(max_length=255)
    partner = models.CharField(max_length=255)
    green = models.BooleanField()
    modified = models.DateTimeField()

    def __str__(self):
        return f"{self.url} - {self.modified}"

    # Factories

    @classmethod
    def grey_result(cls, domain=None):
        """
        Return a grey domain with just the domain name added,
        the time of the and the rest empty.
        """
        return GreenDomain(
            url=domain,
            hosted_by=None,
            hosted_by_id=None,
            hosted_by_website=None,
            partner=None,
            modified=timezone.now(),
        )

    @classmethod
    def from_sitecheck(cls, sitecheck):
        """
        Return a grey domain with just the domain name added,
        the time of the and the rest empty.
        """
        hosting_provider = None
        try:
            hosting_provider = ac_models.Hostingprovider.objects.get(
                pk=sitecheck.hosting_provider_id
            )
        except ac_models.Hostingprovider.DoesNotExist:
            logger.warning(
                ("We expected to find a provider for this sitecheck, " "But didn't. ")
            )
            return cls.grey_result(domain=sitecheck.url)

        return GreenDomain(
            url=sitecheck.url,
            hosted_by=hosting_provider.name,
            hosted_by_id=hosting_provider.id,
            hosted_by_website=hosting_provider.website,
            partner=hosting_provider.partner,
            modified=timezone.now(),
            green=True,
        )

    # Queries
    @property
    def hosting_provider(self) -> typing.Union[ac_models.Hostingprovider, None]:
        """
        Try to find the corresponding hosting provider for this url.
        Return either the hosting providr
        """
        try:
            return ac_models.Hostingprovider.objects.get(pk=self.hosted_by_id)
        except ValueError:
            return None
        except Exception as err:
            logger.error(
                (
                    f"Couldn't find a hosting provider for url: {self.url}, "
                    "and hosted_by_id: {hosted_by_id}."
                )
            )
            logger.exception(err)
            return None

    @classmethod
    def check_for_domain(cls, domain, skip_cache=False):
        """
        Accept a domain, or object that resolves to an IP and check.
        Accepts skip_cache option to perform a full DNS lookup
        instead of looking up a domain by key
        """
        from ..domain_check import GreenDomainChecker

        checker = GreenDomainChecker()

        if skip_cache:
            return checker.perform_full_lookup(domain)

        return GreenDomain.objects.filter(url=domain).first()

    class Meta:
        db_table = "greendomain"
