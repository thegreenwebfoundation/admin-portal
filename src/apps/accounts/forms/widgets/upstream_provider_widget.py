import json

from django import forms
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from dal_select2.widgets import ModelSelect2Multiple


class UpstreamProviderSelectWidget(ModelSelect2Multiple):
    """
    Composite widget: Select2 autocomplete multi-select + per-item
    visibility checkboxes.

    Renders a standard DAL ModelSelect2Multiple (a ``<select multiple>``
    enhanced by Select2) followed by a fieldset of checkboxes — one per
    selected provider — letting the submitter choose whether each
    upstream connection should be visible in the public directory.

    The widget's ``value_from_datadict`` returns a list of dicts::

        [{"provider": "42", "is_public": True}, ...]

    Initial data can be passed in the same format, or as a plain list
    of provider IDs (for backwards compatibility).
    """

    def build_attrs(self, base_attrs, extra_attrs=None):
        """Add data attribute so JS can find this widget."""
        attrs = super().build_attrs(base_attrs, extra_attrs)
        attrs["data-upstream-visibility-widget"] = ""
        return attrs

    @property
    def media(self):
        return super().media + type(super().media)(
            js=("accounts/js/upstream_provider_visibility.js",),
        )

    def _normalize_initial(self, value):
        """
        Normalize initial value to a list of {"provider": id, "is_public": bool}.
        Accepts:
        - list of dicts (new format)
        - list of IDs (legacy format, defaults is_public=True)
        - a single dict
        - a single ID
        - model instances
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
                result.append({"provider": pid, "is_public": item.get("is_public", True), "provider_name": item.get("provider_name")})
            elif hasattr(item, "pk"):
                result.append({"provider": str(item.pk), "is_public": True})
            elif item:
                result.append({"provider": str(item), "is_public": True})
        return result

    def render(self, name, value, attrs=None, renderer=None, **kwargs):
        """
        Render the Select2 multi-select, then append the visibility
        checkbox fieldset below it.
        """
        # Normalize the value to a format the underlying SelectMultiple
        # understands (list of PK strings) before passing to super().
        items = self._normalize_initial(value)
        pk_values = [item["provider"] for item in items]

        select_html = super().render(name, pk_values, attrs, renderer, **kwargs)

        field_id = attrs.get("id", name) if attrs else name

        visibility_html = self._render_visibility_list(name, field_id, items)

        return mark_safe(select_html + visibility_html)

    def _render_visibility_list(self, name, field_id, items):
        """Render the fieldset of per-provider visibility checkboxes."""
        if not items:
            return format_html(
                '<fieldset class="upstream-visibility-list mt-3" '
                'id="{}" hidden>'
                '<legend class="text-sm font-medium mb-1">'
                "Selected providers — show in public directory?"
                "</legend>"
                '<div class="upstream-visibility-rows"></div>'
                '<div class="sr-only" aria-live="polite" '
                'id="{}_announcer"></div>'
                "</fieldset>",
                f"{field_id}_visibility",
                field_id,
            )

        rows_html = format_html_join(
            "",
            '<div class="upstream-visibility-row flex items-center gap-2 mb-1">'
            '<input type="checkbox" name="{}_visibility_{}" id="{}_visibility_{}" '
            'class="form-checkbox" {} /> '
            '<label for="{}_visibility_{}" class="text-sm">'
                '<span class="upstream-provider-name">{}</span> '
                "— show in public directory"
                "</label>"
                "</div>",
            (
                (
                    name,
                    item["provider"],
                    field_id,
                    item["provider"],
                    "" if item.get("is_public", True) else "",
                    field_id,
                    item["provider"],
                    item.get("provider_name", f"Provider #{item['provider']}"),
                )
                for item in items
            ),
        )

        # JSON data for JS: provider IDs + names for dynamic row management
        js_data = json.dumps(items)

        return format_html(
            '<fieldset class="upstream-visibility-list mt-3" id="{}">'
            '<legend class="text-sm font-medium mb-1">'
            "Selected providers — show in public directory?"
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

    def value_from_datadict(self, data, files, name):
        """
        Read both the provider IDs from the Select2 multi-select and the
        per-provider visibility checkboxes, returning a list of dicts:
        ``[{"provider": "42", "is_public": True}, ...]``
        """
        provider_ids = super().value_from_datadict(data, files, name)
        if not provider_ids:
            return []

        result = []
        for pid in provider_ids:
            checkbox_name = f"{name}_visibility_{pid}"
            is_public = data.get(checkbox_name) == "on"
            result.append({"provider": str(pid), "is_public": is_public})
        return result

    def format_value(self, value):
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

    Extends ``ModelMultipleChoiceField`` so that the DAL widget's
    ``QuerySetSelectMixin`` can access ``self.choices.queryset`` for
    rendering selected options.

    Unlike the parent, this field's ``clean()`` returns a list of dicts::

        [{"provider": <Hostingprovider instance>, "is_public": True}, ...]
    """

    def clean(self, value):
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

