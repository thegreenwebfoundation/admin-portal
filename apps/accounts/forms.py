import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, UsernameField

from django_countries.fields import CountryField
from taggit_labels.widgets import LabelWidget
from taggit.models import Tag
from dal_select2_taggit import widgets as dal_widgets

from apps.accounts.models.hosting import Hostingprovider
from apps.accounts.models.provider_request import ProviderRequest, EvidenceType

from . import models as ac_models
from .utils import tags_choices

User = get_user_model()


class CustomUserCreationForm(forms.ModelForm):
    """
    A reimplementation the normal django UserCreationForm, but
    without the fields used for validating that passwords are
    the same.

    Used in the django admin, by internal staff.

    Validating passwords are the same isn't a responsibility
    of internal staff.
    That is left to the registration form used in
    the AdminRegistrationView, by users directly.
    """

    class Meta:

        model = User

        # we need at least one field defined in a ModelForm.
        # this is typically overridden in the containing
        # CustomUserAdmin
        fields = ("username",)

        # We use a special username field to normalise the submitted,
        # accounting for various text encodings in different locales
        field_classes = {"username": UsernameField}

    def save(self, commit=True):
        """
        Save the information for the given user, setting the
        password using the chosen encryption strategy specified
        in our settings file.
        """
        user = super().save(commit=False)

        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class UserUpdateForm(UserChangeForm):
    """
    A form to show to users outside of the django admin.

    We don't show the password, but we do link to the update form.

    """

    def __init__(self, *args, **kwargs):
        """ """
        super().__init__(*args, **kwargs)
        del self.fields["password"]

    class Meta(UserChangeForm.Meta):
        model = ac_models.User
        fields = ("username", "email")


class HostingAdminForm(forms.ModelForm):

    email_template = forms.ModelChoiceField(
        queryset=ac_models.SupportMessage.objects.all(),
        required=False,
        label="email",
    )

    class Meta:
        model = ac_models.Hostingprovider
        fields = "__all__"
        widgets = {
            "services": LabelWidget(model=Tag),
            "staff_labels": dal_widgets.TaggitSelect2("label-autocomplete"),
        }


class DatacenterAdminForm(forms.ModelForm):
    hostingproviders = forms.ModelMultipleChoiceField(
        queryset=ac_models.Hostingprovider.objects.all(),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name="ac_models.Hostingprovider", is_stacked=False
        ),
    )

    class Meta:
        model = ac_models.Datacenter
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
        model = ac_models.HostingProviderNote
        fields = ["body_text"]


class DatacenterNoteNoteForm(forms.ModelForm):
    """
    A custom form for listing comments on datacenters.
    """

    class Meta:
        model = ac_models.DatacenterNote
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
        model = ac_models.HostingProviderSupportingDocument
        fields = "__all__"


class RegistrationForm1(forms.Form):
    name = forms.CharField(
        max_length=255,
        label="Name",
        help_text="What is the brand or commonly used name for this provider? This will be the name listed in the directory",
    )
    website = forms.URLField(
        max_length=255,
        label="Web address",
        help_text="Add the full URL - don't forget the https:// part",
    )
    description = forms.CharField(
        label="Description",
        help_text="Add the description for this organisation, as you would expect to see it in the search results",
        widget=forms.Textarea,
    )
    country = CountryField().formfield(
        label="Country",
        blank_label="Select country",
        help_text="Which country is this provider based in?",
    )
    city = forms.CharField(max_length=255, label="City", help_text="Add the city")


class RegistrationForm2(forms.Form):
    country = CountryField().formfield(
        label="Country",
        blank_label="Select country",
        help_text="Which country is this provider based in?",
    )
    city = forms.CharField(
        max_length=255,
        label="City",
        help_text="List the closest city to this location",
    )
    services = forms.MultipleChoiceField(
        widget=forms.SelectMultiple,
        required=False,
        choices=tags_choices,
        help_text="The following services are offered in this location:",
    )


class CredentialForm(forms.Form):
    title = forms.CharField(
        max_length=255, label="Title", help_text="Add a descriptive title"
    )
    credential_type = forms.ChoiceField(
        choices=EvidenceType.choices,
        label="Type",
        help_text="enter the kind of evidence here",
    )
    link = forms.URLField(
        label="Link",
        help_text="Add a link to the supporting document online",
        required=False,
    )
    file = forms.FileField(
        label="File upload",
        help_text="Upload the supporting document",
        required=False,
    )

    def clean(self):
        """
        Perform validation - only accept one of: file or link.
        """
        cleaned_data = super().clean()
        link = bool(cleaned_data.get("link"))
        file = bool(cleaned_data.get("file"))

        reason = "Please provide exactly one of the following: link or file."

        if not link and not file:
            raise ValidationError(f"You didn't provide any evidence.\n{reason}")
        # TODO: this doesn't work because file upload doesn't work
        if link and file:
            raise ValidationError(f"You provided both: a link and a file.\n{reason}")


RegistrationForm3 = forms.formset_factory(CredentialForm, extra=1)
