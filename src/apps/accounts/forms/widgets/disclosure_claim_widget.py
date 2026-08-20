from django import forms


class DisclosureClaimCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """
    CheckboxSelectMultiple for the per-disclosure claim picker.

    Renders a visual separator before the "always-on" claims (third-party
    assurance, needs help) so they are visually distinguished from the
    organisation-basis claims the provider selected.

    The separator is injected by the option template
    (``provider_registration/widgets/claim_checkbox_option.html``), which
    emits an ``<hr>`` before the first always-on option.
    """

    option_template_name = (
        "provider_registration/widgets/claim_checkbox_option.html"
    )

    # Slug of the first always-on claim; a separator is rendered before it.
    separator_before = "third-party-independent-assurance"

    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index, subindex, attrs
        )
        option["show_separator"] = str(value) == self.separator_before
        return option
