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
    ProviderRequestEvidence,
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


class DisclosureEditFormMixin:
    """
    Shared logic for editing a single disclosure (draft or live) in one go:
    its details, region scope (locations) and claims.

    Because the ``locations`` and ``claims`` relations use explicit through
    models, Django's default M2M widgets cannot edit them directly. These
    fields are added as checkboxes here, and the admin view persists the
    through-model rows after the form is saved.
    """

    def __init__(self, *args, **kwargs):
        locations_qs = kwargs.pop("locations_qs", [])
        claims_qs = kwargs.pop("claims_qs", [])
        super().__init__(*args, **kwargs)

        instance = self.instance
        self.fields["locations"] = forms.MultipleChoiceField(
            choices=[(str(loc.pk), str(loc)) for loc in locations_qs],
            required=False,
            widget=forms.CheckboxSelectMultiple,
            help_text="Leave empty for Global scope.",
            initial=(
                [str(loc.pk) for loc in instance.locations.all()]
                if instance and instance.pk
                else []
            ),
        )
        self.fields["claims"] = forms.MultipleChoiceField(
            choices=self._build_claim_choices(claims_qs),
            required=False,
            widget=forms.CheckboxSelectMultiple,
            initial=(
                [str(c.pk) for c in instance.claims.all()]
                if instance and instance.pk
                else []
            ),
        )

    @staticmethod
    def _build_claim_choices(claims_qs):
        """
        Return grouped choices for the disclosure claims so they render with
        version headings in the admin checkbox list, mirroring the grouping
        used by the historical bulk edit surface:

        - organisation-basis claims grouped by verification-basis version
        - always-on claims (third-party assurance / needs help) in one group
        """
        from ..models import VerificationBasisVersion

        claims_by_id = {c.pk: c for c in claims_qs}

        grouped = []
        for version_value, version_label in VerificationBasisVersion.choices:
            version_claims = [
                (str(c.pk), c.label)
                for c in claims_by_id.values()
                if c.category == "organisation_basis"
                and c.version == version_value
            ]
            if version_claims:
                grouped.append((f"Version: {version_label}", version_claims))

        always_on = [
            (str(c.pk), c.label)
            for c in claims_by_id.values()
            if c.category in ("third_party_assurance", "needs_help")
        ]
        if always_on:
            grouped.append(("Always available", always_on))

        return grouped


class ProviderRequestEvidenceEditForm(DisclosureEditFormMixin, forms.ModelForm):
    """Edit form for a single draft provider-request disclosure."""

    class Meta:
        model = ProviderRequestEvidence
        fields = (
            "title",
            "description",
            "type",
            "link",
            "file",
            "public",
            "fossil_free_energy_matching",
            "claim_coverage_percentage",
        )


class HostingProviderSupportingDocumentEditForm(
    DisclosureEditFormMixin, forms.ModelForm
):
    """Edit form for a single live hosting-provider disclosure."""

    class Meta:
        model = HostingProviderSupportingDocument
        fields = (
            "title",
            "description",
            "type",
            "url",
            "attachment",
            "public",
            "fossil_free_energy_matching",
            "claim_coverage_percentage",
            "valid_from",
            "valid_to",
        )


