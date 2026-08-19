import json
from typing import Any

from django import forms
from django.forms import Media
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe


class UpstreamProviderSelectWidget(forms.SelectMultiple):
    """
    Composite widget: TomSelect autocomplete multi-select + per-item
    visibility checkboxes.

    Renders a plain ``<select multiple>`` enhanced by TomSelect
    (bundled in ``js/dist/app.bundle.js``) followed by a fieldset of
    checkboxes — one per selected provider — letting the submitter choose
    whether each upstream connection should be visible in the public
    directory.

    The widget's ``value_from_datadict`` returns a list of dicts::

        [{"provider": "42", "is_public": True}, ...]

    Initial data can be passed in the same format, or as a plain list
    of provider IDs (for backwards compatibility).

    When ``show_visibility`` is False, the visibility fieldset is omitted
    and every selected provider is treated as public.
    """

    def __init__(
        self,
        attrs: dict[str, Any] | None = None,
        show_visibility: bool = True,
        url: str | None = None,
        **kwargs,
    ):
        self.show_visibility = show_visibility
        self.url = url
        super().__init__(attrs=attrs)

    def build_attrs(
        self,
        base_attrs: dict[str, Any],
        extra_attrs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        attrs = super().build_attrs(base_attrs, extra_attrs)
        # The JS uses this attribute to identify upstream-provider selects and
        # to decide whether to initialise a TomSelect instance on the page.
        attrs["data-upstream-visibility-widget"] = ""
        if self.url:
            # Make the autocomplete endpoint explicit in the markup so the
            # client-side code does not have to hard-code a URL.
            attrs["data-autocomplete-url"] = reverse(self.url)
        return attrs

    @property
    def media(self) -> Media:
        return Media(
            js=(
                "accounts/js/tomselect-widgets.js",
                "accounts/js/upstream_provider_visibility.js",
            ),
        )

    def _normalize_initial(self, value) -> list[dict[str, Any]]:
        """
        Normalize initial value to a list of {"provider": id, "is_public": bool}.
        Accepts:
        - list of dicts (new format)
        - list of IDs (legacy format, defaults is_public=True)
        - a single dict
        - a single ID
        - model instances

        We need this because sometimes we are working iwth an existing model,
        but sometimes we are working with a provider request submission
        for a totally new provider
        """
        if value is None:
            return []
        if isinstance(value, dict):
            return [value]
        if not isinstance(value, (list, tuple)):
            value = [value]

        result = []
        for item in value:
            if isinstance(item, dict):
                # Normalize provider to a string ID
                pid = item.get("provider")
                if hasattr(pid, "pk"):
                    pid = str(pid.pk)
                else:
                    pid = str(pid)
                entry = {"provider": pid, "is_public": item.get("is_public", True)}
                # Only carry forward provider_name if truthy
                pname = item.get("provider_name")
                if pname:
                    entry["provider_name"] = pname
                result.append(entry)
            elif hasattr(item, "pk"):
                result.append({"provider": str(item.pk), "is_public": True})
            elif item:
                result.append({"provider": str(item), "is_public": True})
        return result

    def _load_provider_names(self, items: list[dict[str, Any]]) -> dict[str, str]:
        """Return a {provider_id: name} map for items missing a provider_name."""
        missing_pks = [
            int(item["provider"])
            for item in items
            if not item.get("provider_name")
        ]
        if not missing_pks:
            return {}

        from apps.accounts.models import Hostingprovider

        return {
            str(p.pk): p.name
            for p in Hostingprovider.objects.filter(pk__in=missing_pks)
        }

    def render(
        self,
        name: str,
        value: Any,
        attrs: dict[str, Any] | None = None,
        renderer=None,
        **kwargs,
    ) -> str:
        """
        Render the TomSelect multi-select, then append the visibility
        checkbox fieldset below it (when ``show_visibility`` is True).
        """
        # Normalize the value to a format the underlying SelectMultiple
        # understands (list of PK strings) before passing to super().
        items = self._normalize_initial(value)

        # Make sure every selected provider has a display name before we render
        # the <option> elements that TomSelect uses for its item labels.
        name_map = self._load_provider_names(items)
        for item in items:
            if not item.get("provider_name"):
                item["provider_name"] = name_map.get(
                    item["provider"], f"Provider #{item['provider']}"
                )

        pk_values = [item["provider"] for item in items]

        # Only render <option> elements for the selected providers. This keeps
        # the markup small; TomSelect will fetch labels for new selections via
        # the autocomplete endpoint.
        original_choices = list(self.choices)
        self.choices = [
            (item["provider"], item["provider_name"])
            for item in items
        ]
        try:
            select_html = super().render(
                name, pk_values, attrs, renderer, **kwargs
            )
        finally:
            self.choices = original_choices

        field_id = attrs.get("id", name) if attrs else name

        if not self.show_visibility:
            return mark_safe(select_html)

        visibility_html = self._render_visibility_list(name, field_id, items)

        return mark_safe(select_html + visibility_html)

    def _render_visibility_list(
        self, name: str, field_id: str, items: list[dict[str, Any]]
    ) -> str:
        """Render the fieldset of per-provider visibility checkboxes."""
        # Look up provider names for any items missing one
        missing_pks = [
            int(item["provider"])
            for item in items
            if not item.get("provider_name")
        ]
        name_map = {}
        if missing_pks:
            from apps.accounts.models import Hostingprovider
            name_map = {
                str(p.pk): p.name
                for p in Hostingprovider.objects.filter(pk__in=missing_pks)
            }

        for item in items:
            if not item.get("provider_name"):
                item["provider_name"] = name_map.get(
                    item["provider"], f"Provider #{item['provider']}"
                )

        if not items:
            return format_html(
                '<fieldset class="upstream-visibility-list mt-3" '
                    'id="{}" hidden>'
                    '<legend class="text-sm font-medium mb-1">'
                        "Providers in your upstream supply chain. Providers with checked checkboxes count as 'public'."
                    "</legend>"
                    '<div class="upstream-visibility-rows"></div>'
                    '<div class="sr-only" aria-live="polite" '
                    'id="{}_announcer"></div>'
                "</fieldset>",
                f"{field_id}_visibility",
                field_id,
            )

        # render our list of checkboxes the chosen providers
        rows_html = format_html_join(
            "",
            '<div class="upstream-visibility-row flex items-center gap-2 mb-1" '
            'data-provider-id="{}">'
            '<input type="checkbox" name="{}_visibility_{}" id="{}_visibility_{}" '
            'class="form-checkbox" {} /> '
            '<label for="{}_visibility_{}" class="text-sm">'
                '<span class="upstream-provider-name">{}</span> '
                '<span class="visibility-label visibility-public" {}>— show in public directory</span> '
                '<span class="visibility-label visibility-hidden" {}>— will not be shown in public directory</span> '
                "</label>"
                "</div>",
            (
                (
                    item["provider"],
                    name,
                    item["provider"],
                    field_id,
                    item["provider"],
                    "checked" if item.get("is_public", True) else "",
                    field_id,
                    item["provider"],
                    item.get("provider_name", f"Provider #{item['provider']}"),
                    "" if item.get("is_public", True) else "hidden",
                    "hidden" if item.get("is_public", True) else "",
                )
                for item in items
            ),
        )

        # JSON data for JS: provider IDs + names for dynamic row management.
        # Escape < and > to prevent XSS via provider names breaking out of
        # the <script> tag.
        js_data = json.dumps(items).replace("<", "\\u003c").replace(">", "\\u003e")

        return format_html(
            '<fieldset class="upstream-visibility-list mt-3" id="{}">'
            '<legend class="text-sm font-medium mb-1">'
            "Providers in your upstream supply chain. Providers with checked checkboxes count as 'public'."
            "</legend>"
            '<div class="upstream-visibility-rows">{}</div>'
            '<script type="application/json" id="{}_data">{}</script>'
            '<div class="sr-only" aria-live="polite" id="{}_announcer"></div>'
            "</fieldset>",
            f"{field_id}_visibility",
            rows_html,
            field_id,
            mark_safe(js_data),
            field_id,
        )

    def value_from_datadict(
        self, data: dict[str, Any], files: Any, name: str
    ) -> list[dict[str, Any]]:
        """
        Read both the provider IDs from the multi-select and the
        per-provider visibility checkboxes, returning a list of dicts:
        ``[{"provider": "42", "is_public": True}, ...]``
        """
        provider_ids = super().value_from_datadict(data, files, name)
        if not provider_ids:
            return []

        result = []
        for pid in provider_ids:
            checkbox_name = f"{name}_visibility_{pid}"
            if self.show_visibility:
                is_public = data.get(checkbox_name) == "on"
            else:
                # When no visibility checkboxes are rendered, default to the
                # model's default (public).
                is_public = True
            result.append({"provider": str(pid), "is_public": is_public})
        return result

    def format_value(self, value: Any) -> list[str]:
        """
        Convert the list-of-dicts value into the format that the
        underlying SelectMultiple expects (a list of PKs as strings).
        """
        items = self._normalize_initial(value)
        result = []
        for item in items:
            pid = item["provider"]
            if hasattr(pid, "pk"):
                pid = pid.pk
            result.append(str(pid))
        return result


class UpstreamProviderChoiceField(forms.ModelMultipleChoiceField):
    """
    Custom form field for selecting upstream providers with per-item
    visibility. Pairs with :class:`UpstreamProviderSelectWidget`.

    Unlike the parent, this field's ``clean()`` returns a list of dicts::

        [{"provider": <Hostingprovider instance>, "is_public": True}, ...]
    """

    def clean(self, value: Any) -> list[dict[str, Any]]:
        """
        Override clean to prevent the parent from converting the widget's
        list-of-dicts into a queryset. We validate the provider IDs against
        the queryset ourselves.
        """
        # value is the output of the widget's value_from_datadict:
        # a list of {"provider": str_id, "is_public": bool} dicts
        if value in self.empty_values or not value:
            return []

        if not isinstance(value, list):
            raise forms.ValidationError("Expected a list of upstream provider selections.")

        result = []
        for item in value:
            pid = item.get("provider")
            is_public = item.get("is_public", True)
            if not pid:
                continue
            try:
                provider = self.queryset.get(pk=pid)
            except (ValueError, LookupError, self.queryset.model.DoesNotExist):
                raise forms.ValidationError(
                    f"Provider with ID '{pid}' is not a valid choice."
                )
            result.append({"provider": provider, "is_public": is_public})
        return result
