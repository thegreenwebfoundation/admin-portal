import datetime

from dal_select2_taggit import widgets as dal_widgets
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UsernameField
from django.core.exceptions import ValidationError
from django.db.models.query import QuerySet
from django.forms.formsets import BaseFormSet
from django.forms.utils import ErrorList
from django.utils.safestring import mark_safe
from django_countries.fields import CountryField
from dal_select2_taggit import widgets as dal_widgets
from betterforms.multiform import MultiModelForm
from convenient_formsets import ConvenientBaseModelFormSet
from file_resubmit.widgets import ResubmitFileWidget
from taggit_labels.widgets import LabelWidget

from apps.accounts.models.provider_request import ProviderRequest, ProviderRequestStatus, VerificationBasis

from . import models as ac_models
from django.utils.safestring import mark_safe


User = get_user_model()


class AlwaysChangedModelFormMixin:
    """
    A mixin for ModelForms that makes sure that a form with this Mixin
    is always marked as changed in checks like `has_changed()`.
    Used in form wizards containing formsets, to return true for all forms
    in a formset, so that all data is saved at the end of the wizard.
    """

    def has_changed(self):
        """
        Always returns True, so that the form is always marked as changed.
        """
        return True


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
            "services": LabelWidget(model=ac_models.Service),
            "verification_bases": LabelWidget(model=ac_models.VerificationBasis),
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

class OrgDetailsForm(forms.ModelForm):
    """
    Part of multi-step registration form (screen 1)
    """

    name = forms.CharField(
        max_length=255,
        label="What is your organisation's name?",
        help_text=(
            "What is the brand or commonly used name? This will be the publicly listed"
            " name."
        ),
    )
    website = forms.URLField(
        max_length=255,
        label="What is your organisation's primary website?",
        help_text="Add the full URL - please include the https:// part.",
    )
    description = forms.CharField(
        label="How do you describe your organisation?",
        help_text=(
            "Add a single paragraph about your organisation, as you would expect to see"
            " in search results."
        ),
        widget=forms.widgets.Textarea,
        max_length=1000,
    )
    authorised_by_org = forms.TypedChoiceField(
        label="Do you work for the organisation seeking verification?",
        help_text=(
            "We ask this so we know whether you are speaking on behalf of the"
            " organisation seeking verification or not. It's still ok to submit info if you don't work for"
            " them, but we need to know, so we don't misrepresent anything."
        ),
        widget=forms.RadioSelect,
        choices=(
            (
                "True",
                (
                    "Yes, I work for the organisation seeking verification. I am authorised to speak on"
                    " its behalf."
                ),
            ),
            (
                "False",
                "No, I do not",
            ),
        ),
        empty_value=None,
        coerce=lambda x: x == "True",
    )

    class Meta:
        model = ac_models.ProviderRequest
        fields = ["name", "website", "description", "authorised_by_org"]


class ServicesForm(forms.ModelForm):
    """
    Part of multi-step registration form (screen 2)
    """

    services = forms.MultipleChoiceField(
        choices=ProviderRequest.get_service_choices,
        widget=forms.CheckboxSelectMultiple,
        label="Which services does your organisation offer?",
        help_text=mark_safe(
            'Choose all the services that your organisation offers. <a href="https://www.thegreenwebfoundation.org/directory/services-offered/" target="_blank" rel="noopener noreferrer">More information on our services</a>.'  # noqa
        ),
    )

    def __init__(self, *args, **kwargs):
        """
        Implement injecting initial values for services field (for editing existing objects).
        By default the initial value is passed as a queryset,
        but TaggableManager does not handle that well - we pass a list instead.
        """
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")
        if instance:
            self.initial = {"services": [s for s in instance.services.slugs()]}

    class Meta:
        model = ac_models.ProviderRequest
        fields = ["services"]


class BasisForVerificationForm(forms.ModelForm):
    """
    Part of multi-step registration form (screen 3)
    """

    verification_bases = forms.MultipleChoiceField(
        choices=ProviderRequest.get_verification_bases_choices,
        widget=forms.CheckboxSelectMultiple,
        label="On what basis are you seeking verification?",
        help_text=mark_safe(
          "The Green Web Dataset lists providers taking actions to <b>avoid</b>, <b>reduce</b>, or <b>offset</b> "
          "the greenhouse gas emissions caused by using electricity to provide their services. "
          "<p>On the next page, we will ask you to provide evidence that allows us to verify the steps you are taking. "
          "So before continuing, we strongly recommend you understand the kinds of evidence required based on your organisations circumstances. "
          "We've written about this on the <i><b><a target=\"_blank\" href=\"https://www.thegreenwebfoundation.org/what-we-accept-as-evidence-of-green-power/\">What we accept as evidence of green power?</a></i></b> page on our website.</p>"
          "<p>When you are ready to continue, please select one or more of the statements below that apply to your organisation.</p>"
        ),
    )

    def __init__(self, *args, **kwargs):
        """
        Implement injecting initial values for bases_for_verification field (for editing existing objects).
        By default the initial value is passed as a queryset,
        but TaggableManager does not handle that well - we pass a list instead.
        """
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")
        if instance:
            self.initial = {"verification_bases": [b for b in instance.verification_bases.slugs()]}

    class Meta:
        model = ac_models.ProviderRequest
        fields = ["verification_bases"]


class CredentialForm(AlwaysChangedModelFormMixin, forms.ModelForm):
    class Meta:
        model = ac_models.ProviderRequestEvidence
        exclude = ["request"]
        labels = {"file": "File upload"}
        # define the ordering of the fields
        fields = ["type", "title", "link", "file", "description", "public"]
        help_texts = {
            "type": (
                "What kind of evidence are you adding? Choose from the dropdown list."
            ),
            "title": "Give this piece of evidence a title.",
            "description": "What else should we know about this evidence? If it does not clearly name your organisation, please add a sentence outlining why.",  # noqa
            "link": "Provide a link to a supporting document. Include the https:// part.",  # noqa
            "file": "OR upload a supporting document in PDF or image format.",
            "public": (
                "By checking this box you agree to place this evidence in the public domain, and it being cited publicly"  # noqa
                " to support your organisation's sustainability claims<sup>**</sup>."
            ),
        }
        # we're using this widget to retain the files submitted in the form
        # in case of ValidationError being raised
        widgets = {"file": ResubmitFileWidget}


class MoreConvenientFormset(ConvenientBaseModelFormSet):
    def __init__(self, *args, **kwargs):
        """
        Override a whacky ModelFormSets behavior in order to
        render initial forms correctly (important for the preview step!)

        Problem #1: ModelFormSets take "initial" argument to populate initial forms,
        but the value is truncated to the number of "extra" forms
        as configured in the modelformset_factory. Example:

        MyModelFormset.extra = 1
        formset = MyModelFormset(initial=[data1, data2, data3])
        formset.forms == 1 # and with this fix it's 3 as we'd expect

        Problem #2: FormSets that have min_num argument passed greater than 0
        (requiring at least 1 form to be submitted) have some internal magic that
        manipulate the number of extra forms based on that. For those the value
        needs to be decreased to acommodate for that. Otherwise the preview step
        displays empty extra forms. Example:

        MyModelFormset.extra = 1
        MyModelFormset.min_num = 1
        formset = MyModelFormset(initial=[data1])
        formset.forms == 2 # and with this fix it's 1 as we'd expect

        Docs: https://docs.djangoproject.com/en/3.2/topics/forms/modelforms/#id2

        TODO: come back here to investigate the validation of initial extra forms in ModelFormSets
        """
        initial = kwargs.get("initial")
        if initial:
            self.extra = len(initial) - self.min_num
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        """
        Built-in BaseModelFormSet uses model's default manager get_queryset,
        which returns all objects. As a consequence
        the formset would display all available objects.

        Docs: https://docs.djangoproject.com/en/3.2/topics/forms/modelforms/#changing-the-queryset

        We change that behavior so that unless a "queryset"
        parameter is passed to the formset (i.e. in editing mode),
        empty queryset should be returned.
        """
        if self.queryset is None:
            return self.model.objects.none()
        return super().get_queryset()

    def clean(self):
        """
        ConvenientBaseFormset validates empty forms in a quirky way:
        it treats them as valid with cleaned_data = {}.

        This helper class overrides this behavior: empty forms are not allowed.
        Additionally, it validates if there is no duplicated data in the formset.
        """
        super().clean()

        seen = []
        for form in self.forms:
            # we strip the cleaned_data dict from "id" so that finding duplicated values
            # works for both: new and existing entries
            form_data = {
                key: value for key, value in form.cleaned_data.items() if key != "id"
            }
            # handle initial data
            if form.initial:
                form_data.update(**form.initial)
            if not bool(form_data):
                e = ValidationError(
                    "This row has no information - please complete or delete it",
                    code="empty",
                )
                form.add_error(None, e)
            if form_data in seen:
                e = ValidationError(
                    "Found a duplicated entry in the form, please remove the duplicate",
                    code="duplicate",
                )
                form.add_error(None, e)
            seen.append(form_data)


# Part of multi-step registration form (screen 3).
# Uses ConvenientBaseFormSet to display add/delete buttons
# and manage the forms inside the formset dynamically.
class GreenEvidenceForm(
    forms.modelformset_factory(
        model=ac_models.ProviderRequestEvidence,
        form=CredentialForm,
        extra=0,
        formset=MoreConvenientFormset,
        validate_min=True,
        min_num=1,
        can_delete=True,
        can_delete_extra=True,
    )
):
    def non_form_errors(self):
        """
        Overwrite the error message when too few forms submitted.

        TODO: after upgrading to Django 4.1 use `too_few_forms` from this API instead:
        https://docs.djangoproject.com/en/4.1/topics/forms/formsets/#formsets-error-messages
        """
        errors = super().non_form_errors()
        original_msg = "Please submit at least 1 form."
        target_msg = "Please submit at least one row of evidence."
        return ErrorList(error.replace(original_msg, target_msg) for error in errors)


class IpRangeForm(AlwaysChangedModelFormMixin, forms.ModelForm):
    start = forms.GenericIPAddressField()
    end = forms.GenericIPAddressField()

    class Meta:
        model = ac_models.ProviderRequestIPRange
        exclude = ["request"]


class AsnForm(AlwaysChangedModelFormMixin, forms.ModelForm):
    class Meta:
        model = ac_models.ProviderRequestASN
        exclude = ["request"]


IpRangeFormset = forms.modelformset_factory(
    model=ac_models.ProviderRequestIPRange,
    form=IpRangeForm,
    formset=MoreConvenientFormset,
    extra=0,
    can_delete=True,
    can_delete_extra=True,
)
AsnFormset = forms.modelformset_factory(
    model=ac_models.ProviderRequestASN,
    form=AsnForm,
    formset=MoreConvenientFormset,
    extra=0,
    can_delete=True,
    can_delete_extra=True,
)


class ExtraNetworkInfoForm(forms.ModelForm):
    """
    A form to capture other information relating to a provider's
    network footprint. If data is missing, or a provider is using a
    carbon.txt file to share information they would add using this form.
    """

    missing_network_explanation = forms.CharField(
        label="Alternative network explanation",
        required=False,
        widget=forms.widgets.Textarea,
    )

    network_import_required = forms.BooleanField(
        label="Network location import required",
        help_text=(
            "Select this option if you have a CSV file of network addresses to import. "
            "We will contact you separately to arrange a bulk import of your data."
        ),
        initial=False,
        required=False,
    )

    class Meta:
        model = ac_models.ProviderRequest
        fields = ["missing_network_explanation", "network_import_required"]


class BetterMultiModelForm(MultiModelForm):
    """
    MultiModelForm does not support injecting "instance" paramater
    as querysets when child forms are ModelFormSets.
    See more details: https://github.com/fusionbox/django-betterforms/issues/48

    This helper class fixes that.
    """

    def get_form_args_kwargs(self, key, args, kwargs):
        fargs, fkwargs = super().get_form_args_kwargs(key, args, kwargs)
        try:
            if isinstance(self.instances[key], QuerySet):
                fkwargs["queryset"] = self.instances[key]
                fkwargs.pop("instance")
        except KeyError:
            pass
        return fargs, fkwargs


class NetworkFootprintForm(BetterMultiModelForm):
    """
    Part of multi-step registration form (screen 4).

    Uses MultiModelForm to display different forms and formsets in
    a single form.

    Uses ConvenientBaseFormSet to display add/delete buttons
    and manage the forms inside the formsets dynamically.
    """

    # We have to set base_fields to a dictionary because
    # the WizardView tries to introspect it.
    base_fields = {}

    # The `form` object passed to the template will have
    # 2 separate formsets inside,
    # accessible by the keys defined as below
    form_classes = {
        "ips": IpRangeFormset,
        "asns": AsnFormset,
        "extra": ExtraNetworkInfoForm,
    }

    def clean(self):
        """
        Validate that a form at least has:
        1. some IP and/or AS data
        2. or some explanation as to why this network data is missing

        """
        super().clean()

        # fetch our forms
        ip_form = self.forms["ips"]
        asn_form = self.forms["asns"]
        explanation_form = self.forms["extra"]

        # is there any description we can read?
        explanation_present = any(explanation_form.cleaned_data.values())

        # do any of the two network formsets contain valid network data?
        network_data_present = ip_form.forms or asn_form.forms

        if not network_data_present and not explanation_present:
            e = ValidationError(
                "If you don't have any network info, you need to at least provide "
                "an explanation for why this is the case.",
                code="no_network_no_explanation",
            )
            self.add_crossform_error(e)

        return self.cleaned_data


class ConsentForm(forms.ModelForm):
    """
    Part of multi-step registration form (screen 5).

    Set of agreements that the user consents to (or not) to by submitting the request.
    """

    data_processing_opt_in = forms.BooleanField(
        required=True,
        initial=False,
        label=(
            "I consent to my submitted information being stored and processed to allow"
            " a response to my inquiry"
        ),
        label_suffix="",
        help_text=mark_safe(
            '<a href="https://www.thegreenwebfoundation.org/privacy-statement/" target="_blank" rel="noopener noreferrer">See our full privacy notice</a>'  # noqa
        ),
    )
    newsletter_opt_in = forms.BooleanField(
        required=False,
        initial=False,
        label="Sign me up to the newsletter",
        label_suffix="",
        help_text=(
            "We run a newsletter, Greening Digital, where we share actionable news"
            " about greening the web and a sustainable digital transition. You can"
            " unsubscribe at any time."
        ),
    )

    class Meta:
        model = ac_models.ProviderRequest
        fields = ["data_processing_opt_in", "newsletter_opt_in"]


class LocationForm(AlwaysChangedModelFormMixin, forms.ModelForm):
    name = forms.CharField(
        max_length=255,
        label="Location name",
        help_text=(
            "Use a name your customers would recognise for this location. For example 'Main headquarters', 'Regional office', 'eu-west datacentre'."  # noqa
        ),
        required=False,
        widget=forms.widgets.TextInput(
            attrs={
                "placeholder": ("Location name"),
                "size": 60,
            },
        ),
    )

    city = forms.CharField(
        max_length=255,
        label="City",
        help_text=(
            "If this location is not within a given city, choose the nearest city."
        ),
        widget=forms.widgets.TextInput(
            attrs={
                "placeholder": ("City"),
                "size": 60,
            },
        ),
    )

    country = CountryField(
        blank_label="(Select a country)",
    ).formfield(
        label="Country",
        help_text="Choose a country from the list.",
    )

    class Meta:
        model = ac_models.ProviderRequestLocation
        fields = ["country", "city", "name"]


# Part of multi-step registration form (screen 2).
# Uses ConvenientBaseFormSet to display add/delete buttons
# and manage the forms inside the formset dynamically.
LocationsFormSet = forms.modelformset_factory(
    model=ac_models.ProviderRequestLocation,
    form=LocationForm,
    extra=0,
    formset=MoreConvenientFormset,
    validate_min=True,
    min_num=1,
    can_delete=True,
    can_delete_extra=True,
)


class LocationExtraForm(forms.ModelForm):
    """
    A form for information relating to the location step, not a to a
    single one of the locations listed on the location step.
    """

    location_import_required = forms.BooleanField(
        label="Bulk location import required",
        help_text=(
            "Select this option if you have more than ten locations to add. "
            "We ask you to add at least one location now. "
            "We will contact you separately to arrange a bulk import of your data."
        ),
        initial=False,
        required=False,
    )

    class Meta:
        model = ac_models.ProviderRequest
        fields = ["location_import_required"]


class LocationStepForm(BetterMultiModelForm):
    """
    A form to support at least one location as well as
    allowing a provider to flag up that they have a
    significant number of locations to import.

    """

    # We have to set base_fields to a dictionary because
    # the WizardView tries to introspect it.
    base_fields = {}

    # The `form` object passed to the template will have
    # 1 formset and one form, accessible by the
    # keys defined as below
    form_classes = {
        "locations": LocationsFormSet,
        "extra": LocationExtraForm,
    }

    def non_field_errors(self):
        """
        MultiForms do not work with formsets by default:
        the non_form_errors in formsets are not propagated correctly.

        We overwrite this method so that non_form_errors are concatenated
        with MultiForm's non_field_errors.
        """
        errors = super().non_field_errors()
        for form in self.forms.values():
            if isinstance(form, BaseFormSet):
                # replace the original message to contain more precise information
                # TODO: after upgrading to Django 4.1 use `too_few_forms` from this API instead:
                # https://docs.djangoproject.com/en/4.1/topics/forms/formsets/#formsets-error-messages
                original_msg = "Please submit at least 1 form."
                target_msg = "Please submit at least 1 location."
                if self.forms["extra"]["location_import_required"].value():
                    target_msg = f"You've selected the bulk import option, but we still need to know where your headquarters are. {target_msg}"
                formset_errors = [
                    error.replace(original_msg, target_msg)
                    for error in form.non_form_errors()
                ]
                errors.extend(formset_errors)
        return errors


class PreviewForm(forms.Form):
    """
    A dummy Form without any data.

    It is used as a placeholder for the last step of the Wizard,
    in order to render a preview of all data from the previous steps.
    """

    pass


class LinkedDomainFormStep0(forms.ModelForm):
    """
    First step of the Domain Linking process.
    there is currently only one form as the second step just uses
    the dummy PreviewForm with a custom template.
    """

    is_primary = forms.TypedChoiceField(
        label="Is this your primary domain?",
        help_text=(
            "Select this option if this domain represents your own hosting provider "
            "itself, rather than a customer or some other entity."
        ),
       coerce=lambda x: x == 'True',
       choices=((True, 'This is my primary domain'), (False, 'This is the domain of a customer or some other entity.')),
       required=True,
       widget=forms.RadioSelect
    )

    class Meta:
        model = ac_models.LinkedDomain
        fields = ["domain", "is_primary"]

