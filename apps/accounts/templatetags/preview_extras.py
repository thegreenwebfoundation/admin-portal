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
def render_as_linked_providers(value):
    """
    Attempts to map linked provider IDs to provider names
    based on a database query.
    """
    if not value:
        return None
    providers = Hostingprovider.objects.filter(id__in=value)
    if providers:
        # make sure name is safely included in the HTML
        list_items = format_html(
            "<ul>{}</ul>",
            format_html_join(",", "<li>{}</li>", ((prov.name,) for prov in providers)),
        )
        return list_items
    return None


@register.filter
def exclude_preview_fields(form):
    """
    On preview, exclude fields "id" and "delete" from forms
    """
    return [field for field in form if field.label.lower() not in ["id", "delete"]]
