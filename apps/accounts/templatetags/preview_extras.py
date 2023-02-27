from django.template.defaultfilters import yesno
from django import template

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
    # then see if value should be filtered with "yesno"
    if str(value).lower() in "true,false,none,on,off":
        return yesno(value, arg)
    return value
