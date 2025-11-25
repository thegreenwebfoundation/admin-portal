import ipaddress
import logging

import dramatiq
import pika
import tld

from django.db import models
from django.utils import timezone
from django_mysql import models as dj_mysql_models
from django_mysql import models as mysql_models
from model_utils import models as mu_models

from apps.greencheck.validators import validate_ip_range

from ...accounts import models as ac_models
from .. import choices as gc_choices
from ..tasks import process_log

from .fields import IpAddressField
from .site_check import SiteCheck

logger = logging.getLogger(__name__)


class GreencheckIp(mu_models.TimeStampedModel):
    """
    An IP Range associated with a hosting provider, to act as a way to
    link it to the sustainability claims by the company.
    """

    active = models.BooleanField(null=True)
    ip_start = IpAddressField()
    ip_end = IpAddressField(db_column="ip_eind")
    hostingprovider = models.ForeignKey(
        ac_models.Hostingprovider, db_column="id_hp", on_delete=models.CASCADE
    )

    def clean(self):
        """
        Model-level validation: check if IP range is valid.

        This will not be called automatically on Model.save()!
        It needs an explicit call, either:
        - Model.clean()
        - Model.full_clean()
        - ModelForm.is_valid()
        - ModelForm.save()
        """
        validate_ip_range(self.ip_start, self.ip_end)

    def ip_range_length(self) -> int:
        """
        Return the length of the ip range beginning at
        ip_start, and ending at ip_end
        """
        end_number = int(ipaddress.ip_address(self.ip_end))
        start_number = int(ipaddress.ip_address(self.ip_start))

        # we add the extra ip to the range length for the
        # case of the start and end ip addresses being the same ip,
        # and to account for the calc undercounting the number
        # of addresses in a network normally returned by `num_addresses`
        extra_one_ip = 1

        return end_number - start_number + extra_one_ip

    def archive(self) -> "GreencheckIp":
        """
        Mark a GreencheckIp as inactive, as a softer alternative to deletion,
        returning the Greencheck IP for further processing.
        """
        self.active = False
        self.save()
        return self

    def unarchive(self) -> "GreencheckIp":
        """
        Mark a GreencheckIp as inactive, as a softer alternative to deletion,
        returning the Greencheck IP for further processing.
        """
        self.active = True
        self.save()
        return self

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
        db_table = "greencheck"

    def __str__(self):
        return f"{self.url} - {self.ip}"

    @classmethod
    def log_sitecheck_asynchronous(cls, sitecheck):
        """
        Asynchronously logs a sitecheck to the greencheck table
        """
        try:
            process_log.send(sitecheck.asdict())
        except (
            pika.exceptions.AMQPConnectionError,
            dramatiq.errors.ConnectionClosed,
        ):
            logger.warn("RabbitMQ not available, not logging to RabbitMQ")
        except Exception as err:
            logger.exception(f"Unexpected error of type {err}")


    @classmethod
    def log_greendomain_asynchronous(cls, green_domain):
        sitecheck = SiteCheck.from_greendomain(green_domain)
        cls.log_sitecheck_asynchronous(sitecheck)

    @classmethod
    def log_sitecheck_synchronous(cls, sitecheck):
        """
        Synchronously logs a sitecheck to the greencheck table - called from
        within the dramatiq worker
        """
        if sitecheck.url is None:
            return {
                "status": "Sitecheck has no URL. Skipping.",
                "sitechcek": sitecheck,
            }

        try:
            fixed_tld = tld.get_tld(sitecheck.url, fix_protocol=True)
        except tld.exceptions.TldDomainNotFound:
            if sitecheck.url == "localhost":
                return {
                    "status": "We can't look up localhost. Skipping.",
                    "sitecheck": sitecheck,
                }

            try:
                ipaddress.ip_address(sitecheck.url)
                fixed_tld = ""
            except Exception:
                logger.warning(
                    (
                        "not a domain, or an IP address, not logging. "
                        f"Sitecheck results: {sitecheck}"
                    )
                )
                return {"status": "Error", "sitecheck": sitecheck}

        except Exception:
            logger.exception(
                (
                    "Unexpected error. Not logging the result. "
                    f"Sitecheck results: {sitecheck}"
                )
            )
            return {"status": "Error", "sitecheck": sitecheck}

        if sitecheck.hosting_provider_id is not None:
            check = Greencheck.objects.create(
                hostingprovider=sitecheck.hosting_provider_id,
                greencheck_ip=sitecheck.match_ip_range or 0,
                date=sitecheck.checked_at,
                green="yes",
                ip=sitecheck.ip or 0,
                tld=fixed_tld,
                type=sitecheck.match_type,
                url=sitecheck.url,
            )
            logger.debug(f"Greencheck logged: {check}")
        else:
            check = Greencheck.objects.create(
                date=sitecheck.checked_at,
                green="no",
                ip=sitecheck.ip or 0,
                tld=fixed_tld,
                url=sitecheck.url,
            )
            logger.debug(f"Greencheck logged: {check}")

        # return result so we can inspect if need be
        return { "status": "OK", "sitecheck": sitecheck, "res": check }


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
    ip_start = IpAddressField()
    ip_end = IpAddressField(db_column="ip_eind")
    status = models.TextField(choices=gc_choices.StatusApproval.choices)

    def clean(self):
        """
        Model-level validation: check if IP range is valid.

        This will not be called automatically on Model.save()!
        It needs an explicit call, either:
        - Model.clean()
        - Model.full_clean()
        - ModelForm.is_valid()
        """
        validate_ip_range(self.ip_start, self.ip_end)

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

    def archive(self) -> "GreencheckASN":
        """
        Mark a GreencheckASN as inactive, as a softer alternative to deletion,
        returning the Greencheck ASN for further processing.
        """
        self.active = False
        self.save()
        return self

    def unarchive(self) -> "GreencheckASN":
        """
        Mark a GreencheckASN as inactive, as a softer alternative to deletion,
        returning the Greencheck ASN for further processing.
        """
        self.active = True
        self.save()
        return self

    def __str__(self):
        active_state = "Inactive"
        if self.active:
            active_state = "Active"

        return f"{self.hostingprovider} - {self.asn} - {active_state}"

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
                active=True,
                hostingprovider=self.hostingprovider,
                asn=self.asn,
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


