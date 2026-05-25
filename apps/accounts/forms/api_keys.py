from django import forms

from ..models import APIKey


class APIAccessForm(forms.Form):
    api_access_motivation = forms.CharField(
        widget=forms.Textarea(), required=True,
        label="What is your intended use case?",
        help_text="It's very useful to us to understand how and why people are using our data and services. Please tell us a little about how you plan to use our APIs."
    )

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
