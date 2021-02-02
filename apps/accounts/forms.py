from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple

from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, Datacenter, Hostingprovider


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = ("username", "email")


class HostingAdminForm(forms.ModelForm):
    email_template = forms.ChoiceField(
        choices=[
            ("additional-info.txt", "I need more information"),
            ("pending-removal.txt", "Pending removal"),
        ],
        required=False,
        label="email",
    )

    class Meta:
        model = Hostingprovider
        fields = "__all__"


class DatacenterAdminForm(forms.ModelForm):
    hostingproviders = forms.ModelMultipleChoiceField(
        queryset=Hostingprovider.objects.all(),
        required=False,
        widget=FilteredSelectMultiple(verbose_name="Hostingprovider", is_stacked=False),
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
