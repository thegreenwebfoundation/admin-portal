from django import forms

from ..models import LinkedDomain

class LinkedDomainFormStep0(forms.ModelForm):
    """
    First step of the Domain Linking process.
    there is currently only one form as the second step just uses
    the dummy PreviewForm with a custom template.
    """

    domain = forms.CharField(
        help_text=(
            "Enter a valid domain name, for example: <strong>thegreenwebfoundation.org</strong>"
        )
    )

    is_primary = forms.TypedChoiceField(
        label="Is this your organisation's primary domain?",
        # help_text=(
        #     "Select this option if this domain represents your own hosting provider "
        #     "itself, rather than a customer or some other entity."
        # ),
       coerce=lambda x: x == 'True',
       choices=((True, "This is the organisation's primary domain."), (False, "This is a subdomain, a domain for another entity, or a customer's domain.")),
       required=True,
       widget=forms.RadioSelect
    )

    class Meta:
        model = LinkedDomain
        fields = ["domain", "is_primary"]
