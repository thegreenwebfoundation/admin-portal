import datetime

from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple

from dal_select2_taggit import widgets as dal_widgets
from taggit_labels.widgets import LabelWidget

from ..models import (
    Datacenter,
    DatacenterNote,
    Hostingprovider,
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


class InlineSupportingDocumentForm(forms.ModelForm):
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

    class Meta:
        model = HostingProviderSupportingDocument
        fields = "__all__"


