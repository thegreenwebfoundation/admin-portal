from django.template.defaultfilters import yesno
from django import template
from apps.accounts.models import Tag


register = template.Library()


@register.filter
def conditional_yesno(value, arg=None):
    """
    Custom template filter that acts like the builtin "yesno" filter,
    but is only applied to certain values.
    """
    # catch empty string case first
    if value == "":
        value = None
    # for some reason yesno does not map "off" to False
    if str(value).lower() == "off":
        value = False
    # then see if value should be filtered with "yesno"
    if str(value).lower() in "true,false,none,on":
        return yesno(value, arg)
    return value


@register.filter
def render_as_services(value):
    """
    Attempts to map slugs in to service names
    based on a database query.
    """
    tags = Tag.objects.filter(slug__in=value)
    if tags:
        return ", ".join([tag.name for tag in tags])
    return None
