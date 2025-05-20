from django.template.defaultfilters import yesno
from django import template
from django.utils.safestring import mark_safe
from apps.accounts.models import Service, VerificationBasis


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
        list_items =  "\n".join([f"<li>{tag.name}</li>" for tag in tags])
        return mark_safe(f"<ul>{list_items}</ul>")
    return None

@register.filter
def exclude_preview_fields(form):
    """
    On preview, exclude fields "id" and "delete" from forms
    """
    return [field for field in form if field.label.lower() not in ["id", "delete"]]
