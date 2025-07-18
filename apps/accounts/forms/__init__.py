from django import forms

from .admin import (
    DatacenterAdminForm,
    DatacenterNoteNoteForm,
    HostingAdminForm,
    HostingProviderNoteForm,
    InlineSupportingDocumentForm,
    PreviewEmailForm,
)

from .linked_domains import (
    LinkedDomainFormStep0
)

from .provider_request_wizard import (
    AsnForm,
    BasisForVerificationForm,
    ConsentForm,
    ExtraNetworkInfoForm,
    GreenEvidenceForm,
    IpRangeForm,
    LocationsFormSet,
    LocationStepForm,
    NetworkFootprintForm,
    OrgDetailsForm,
    ServicesForm,
)

from .user import (
    CustomUserCreationForm,
)


class PreviewForm(forms.Form):
    """
    A dummy Form without any data.

    It is used as a placeholder for the last step of the Wizard,
    in order to render a preview of all data from the previous steps.
    """

    pass


