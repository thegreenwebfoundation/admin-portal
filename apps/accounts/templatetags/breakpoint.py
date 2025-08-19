from django import template

register = template.Library()

@register.simple_tag(name="breakpoint", takes_context=True)
def breakpoint_tag(context):
    """
    Launch Python’s debugger in templates.

    See: https://adamj.eu/tech/2024/11/28/django-template-breakpoint/
    """
    exec("breakpoint()", {}, context.flatten())
