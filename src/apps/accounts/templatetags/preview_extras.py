from django import template
from django.template.defaultfilters import mark_safe, yesno
from django.utils.html import format_html, format_html_join

from apps.accounts.models import Hostingprovider, Service, VerificationBasis

register = template.Library()


@register.filter
def conditional_yesno(value, arg=None):
    """
    Custom template filter that acts like the builtin "yesno" filter,
    but is only applied to certain values: explicitly True, False, None and "".
    """
    if value == "":
        value = None
    if str(value).lower() in ["true", "false", "none"]:
        return yesno(value, arg)
    return value


@register.filter
def render_as_services(value):
    """
    Attempts to map slugs in to service names
    based on a database query.
    """
    tags = Service.objects.filter(slug__in=value)
    if tags:
        return ", ".join([tag.name for tag in tags])
    return None


@register.filter
def render_as_verification_bases(value):
    """
    Attempts to map slugs in to verification basis names
    based on a database query.
    """
    tags = VerificationBasis.objects.filter(slug__in=value).distinct()
    if tags:
        # TODO update to use format_html_join instead of mark_safe directly
        list_items = "\n".join([f"<li>{tag.name}</li>" for tag in tags])
        return mark_safe(f"<ul>{list_items}</ul>")
    return None


@register.filter
def render_as_upstream_providers(value):
    """
    Renders a list of upstream provider selections (list of dicts with
    ``provider`` and ``is_public`` keys) as an HTML list, showing the
    provider name and visibility state.
    """
    if not value:
        return None

    # Handle both new format (list of dicts) and legacy format (list of IDs)
    if isinstance(value, list) and value and isinstance(value[0], dict):
        provider_ids = [item["provider"] for item in value]
        providers = {p.id: p for p in Hostingprovider.objects.filter(id__in=provider_ids)}
        list_items = format_html_join(
            "",
            "<li>{} ({})</li>",
            (
                (
                    providers[item["provider"]].name,
                    "public" if item.get("is_public", True) else "hidden",
                )
                for item in value
                if item["provider"] in providers
            ),
        )
        return format_html("<ul>{}</ul>", list_items)

    # Legacy: list of provider IDs
    providers = Hostingprovider.objects.filter(id__in=value)
    if providers:
        list_items = format_html(
            "<ul>{}</ul>",
            format_html_join("", "<li>{}</li>", ((prov.name,) for prov in providers)),
        )
        return list_items
    return None


@register.filter
def exclude_preview_fields(form):
    """
    On preview, exclude fields "id" and "delete" from forms
    """
    return [field for field in form if field.label.lower() not in ["id", "delete"]]
