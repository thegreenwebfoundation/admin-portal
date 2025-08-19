from django import forms
from django.utils.functional import lazy
from django.utils.safestring import mark_safe
from dns.reversename import ipv4_reverse_domain

from ..models import Hostingprovider, ProviderCarbonTxt, ProviderCarbonTxtMotivation, CarbonTxtMotivation
from ..validators import DomainNameValidator

class CarbonTxtStep1Form(forms.Form):

    @staticmethod
    def get_motivation_choices():
        choices = []
        for tag in CarbonTxtMotivation.objects.all():
            classname = "show-description-field" if tag.show_description_field else ""
            label = mark_safe(f"<span class='{classname}'>{tag.name}</span>")
            choices.append((tag.slug, label))
        return choices

    domain = forms.CharField(
        label=mark_safe("<span class='text-base'>Domain</span>"),
        label_suffix="",
        help_text="e.g.: www.greenweb.org, without the https://.",
        validators=[DomainNameValidator()]
    )

    carbon_txt_motivations = forms.MultipleChoiceField(
        choices=lazy(get_motivation_choices, tuple)(),
        widget=forms.CheckboxSelectMultiple(
            attrs={"class": "small-labels with-description-field"},
        ),
        label=mark_safe(
            """
                <span class='text-base leading-none block mb-3'>
                    Tell us a little bit about your business.
                    This will help us tailor the rest of this process to your specific needs.
                </span>
            """
        ),
        label_suffix=""
    )

    carbon_txt_motivation_description = forms.CharField(
        required=False,
        label="",
        label_suffix="",
        help_text="Please tell us a little more about any issues you're having.",
        widget=forms.TextInput(attrs={"class": "description-field hidden", "required": False}),
    )

    def update_provider(self, provider):
        if not self.is_valid():
            return False

        carbon_txt = ProviderCarbonTxt(
            provider_id=provider.id,
            domain = self.cleaned_data["domain"]
        )
        carbon_txt.save()
        for slug in self.cleaned_data["carbon_txt_motivations"]:
            motivation = CarbonTxtMotivation.objects.filter(slug=slug).first()
            description = None
            if motivation.show_description_field:
                description = self.cleaned_data["carbon_txt_motivation_description"]
            provider_motivation = ProviderCarbonTxtMotivation(
                tag_id=motivation.id,
                content_object_id=provider.id,
                description=description,
            )
            provider_motivation.save()

class CarbonTxtStep2Form(forms.Form):

    def update_provider(self, provider):
        try:
            provider.carbon_txt.validate()
            provider.carbon_txt.save()

        except ProviderCarbonTxt.CarbonTxtValidationError as error:
            self.add_error(None, error.message)

class CarbonTxtStep3Form(forms.Form):
    is_delegation_set = forms.BooleanField(widget=forms.HiddenInput(), initial=True)

    def update_provider(self, provider):
        if not self.is_valid():
            return False

        provider.carbon_txt.is_delegation_set = self.cleaned_data["is_delegation_set"]
        provider.carbon_txt.save()
