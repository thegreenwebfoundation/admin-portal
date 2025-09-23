from django.db import models
from model_utils.models import TimeStampedModel

from .abstract import EvidenceType, Label
from .datacenter import (
    Datacenter,
    DatacenterCertificate,
    DatacenterClassification,
    DatacenterCooling,
    DataCenterLocation,
    DatacenterNote,
    DatacenterSupportingDocument,
)
from .provider import (
    Hostingprovider,
    HostingproviderCertificate,
    HostingProviderNote,
    HostingProviderSupportingDocument,
    HostingCommunication,
    Service,
    PartnerChoice,
    ProviderSharedSecret,
    VerificationBasis,
    DOMAIN_HASH_ISSUER_ID,
    GREEN_VIA_CARBON_TXT,
)
from .carbon_txt import (
    CarbonTxtMotivation,
    CarbonTxtDomainResultCache,
    ProviderCarbonTxtMotivation,
    ProviderCarbonTxt,
)

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

