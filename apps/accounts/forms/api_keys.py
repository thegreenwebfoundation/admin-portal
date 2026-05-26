from django import forms
from django.utils.safestring import mark_safe

from ..models import APIKey

class FieldsetRadioSelect(forms.RadioSelect):
    def render(self, name, value, attrs=None, renderer=None):
        html = super().render(name, value, attrs, renderer)
        return mark_safe(f'<fieldset class="mt-2">{html}</fieldset>')

class APIAccessForm(forms.Form):
    api_access_motivation = forms.CharField(
        widget=forms.Textarea(), required=True,
        label="What is your intended use case?",
        help_text="It's very useful to us to understand how and why people are using our data and services. Please tell us a little about how you plan to use our APIs."
    )

    privacy_policy_acceptance = forms.ChoiceField(
        required=False,
        choices=[("Yes", "Yes"), ("No", "No")],
        widget=FieldsetRadioSelect(),
        label=mark_safe("Do you accept our <a href='https://www.thegreenwebfoundation.org/privacy-statement/' target='_blank'>privacy statement</a>?"),
        help_text="We log user activity with authenticated APIs, to better understand how our service is used, and to monitor usage levels - we need your explicit informed consent for this."
    )

    def clean_privacy_policy_acceptance(self):
        acceptance = self.cleaned_data.get("privacy_policy_acceptance")
        if acceptance != "Yes":
            raise forms.ValidationError("You must agree to the privacy policy in order to use the API.")
        return acceptance

    def update_user(self, user):
        user.api_access_motivation = self.cleaned_data["api_access_motivation"]
        user.save()


class APIKeyForm(forms.Form):
    expiry_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        required=False,
        label="Expiry date",
        help_text="An optional expiry date for this key, after which it will no longer be allowed to make requests."
    )
    note = forms.CharField(
        required=False,
        label="Note",
        help_text="An optional note to help you remember who this API key is used by, and what for."
    )

    def create_key(self, user):
        return APIKey.objects.create_key_for_user(user,
            note = self.cleaned_data["note"],
            expiry_date = self.cleaned_data["expiry_date"],
        )

class APIRevokeForm(forms.Form):
    pass
