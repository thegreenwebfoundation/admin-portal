import datetime

from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple

from dal import autocomplete
from dal_select2_taggit import widgets as dal_widgets
from taggit_labels.widgets import LabelWidget

from ..models import (
    Datacenter,
    DatacenterNote,
    DisclosureClaim,
    Hostingprovider,
    HostingProviderLocation,
    HostingProviderNote,
    HostingProviderSupportingDocument,
    Service,
    SupportMessage,
    VerificationBasis,
    CarbonTxtMotivation,
)

class HostingAdminForm(forms.ModelForm):
    email_template = forms.ModelChoiceField(
        queryset=SupportMessage.objects.all(),
        required=False,
        label="email",
    )

    class Meta:
        model = Hostingprovider
        fields = "__all__"
        widgets = {
            "services": LabelWidget(model=Service),
            "verification_bases": LabelWidget(model=VerificationBasis),
            "staff_labels": dal_widgets.TaggitSelect2("label-autocomplete"),
            "carbon_txt_motivations": LabelWidget(model=CarbonTxtMotivation)
        }


class DatacenterAdminForm(forms.ModelForm):
    hostingproviders = forms.ModelMultipleChoiceField(
        queryset=Hostingprovider.objects.all(),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name="ac_models.Hostingprovider", is_stacked=False
        ),
    )

    class Meta:
        model = Datacenter
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields[
                "hostingproviders"
            ].initial = self.instance.hostingproviders.all()

    def save(self, commit=True):
        datacenter = super().save(commit=False)

        if commit:
            datacenter.save()

        if datacenter.pk:
            datacenter.hostingproviders.set(self.cleaned_data["hostingproviders"])
            self.save_m2m()

        return datacenter


class HostingProviderNoteForm(forms.ModelForm):
    """
    A custom form for listing comments on hosting providers
    """

    class Meta:
        model = HostingProviderNote
        fields = ["body_text"]


class DatacenterNoteNoteForm(forms.ModelForm):
    """
    A custom form for listing comments on datacenters.
    """

    class Meta:
        model = DatacenterNote
        fields = ["body_text"]


class PreviewEmailForm(forms.Form):
    """
    An email for sending our form
    """

    title = forms.CharField(label="Email title", max_length=255)
    recipient = forms.EmailField()
    body = forms.CharField(widget=forms.Textarea(attrs={"rows": 20, "cols": 90}))
    message_type = forms.CharField(widget=forms.HiddenInput())
    provider = forms.IntegerField(widget=forms.HiddenInput())

    # TODO
    # check that we have an email before trying to forwarding to an email service


class HostingProviderSupportingDocumentInlineForm(forms.ModelForm):
    """
    Form for editing supporting documents in the hosting provider admin.
    Limits the ``locations`` queryset to the provider's live
    ``HostingProviderLocation`` rows.
    """

    class Meta:
        model = HostingProviderSupportingDocument
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit locations to the provider's live locations.
        #
        # Note: the admin inline derivation omits many-to-many fields with an
        # explicit through model, so ``locations`` may not be present when the
        # form is rendered as part of an inline formset.
        if (
            self.instance
            and self.instance.hostingprovider_id
            and "locations" in self.fields
        ):
            hp = self.instance.hostingprovider
            self.fields["locations"].queryset = HostingProviderLocation.objects.filter(
                hostingprovider=hp
            )
        elif "locations" in self.fields:
            self.fields["locations"].queryset = HostingProviderLocation.objects.none()


class InlineSupportingDocumentForm(HostingProviderSupportingDocumentInlineForm):
    """
    A custom form for listing and uploading supporting documents
    in the Hostingprovider admin.
    """

    def __init__(self, *args, **kwargs):
        """
        For new unbound forms, provide initial values for fields:
        - public
        - valid_from
        - valid_to
        """
        super(InlineSupportingDocumentForm, self).__init__(*args, **kwargs)
        if not self.initial:
            self.initial["public"] = False
            self.initial["valid_from"] = datetime.date.today()
            self.initial["valid_to"] = datetime.date.today() + datetime.timedelta(
                days=365
            )


class EditDisclosureClaimsForm(forms.Form):
    """
    A form for editing which claims each disclosure (supporting document)
    backs, used by the dedicated ``edit_disclosure_claims`` admin view on
    both the Hostingprovider and ProviderRequest admins.

    ``documents`` is a list of disclosure instances (live or draft). For
    each document, a ``ModelMultipleChoiceField`` named ``doc_<pk>`` is
    created, pre-populated from ``doc.claims.all()``.

    This exists because Django's admin inline formsets cannot render M2M
    fields with explicit through models as editable fields — the same
    limitation documented for the disclosure-region links in ADR 3.
    """

    def __init__(self, *args, documents=None, **kwargs):
        super().__init__(*args, **kwargs)
        documents = documents or []
        claim_qs = DisclosureClaim.objects.all().order_by("sort_order", "id")
        for doc in documents:
            field_name = f"doc_{doc.pk}"
            self.fields[field_name] = forms.ModelMultipleChoiceField(
                queryset=claim_qs,
                required=False,
                widget=forms.CheckboxSelectMultiple,
                label=str(doc),
                initial=[c.pk for c in doc.claims.all()],
            )


