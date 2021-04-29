import urllib
from django import template
from django.contrib.auth.models import Group
from django.utils.safestring import mark_safe


import logging
from apps.greencheck import domain_check

register = template.Library()

checker = domain_check.GreenDomainChecker()

console = logging.StreamHandler()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(console)


@register.filter
def make_url(website_string: str) -> str:
    """
    Accept a url, or doman, and turn it into full url,
    adding the protocol if need be
    """
    parsed_url = urllib.parse.urlparse(website_string)
    if not parsed_url.scheme:
        # add the //, so that our url reading code
        # parses it properly
        return f"https://{website_string}"

    return website_string


@register.simple_tag
def link_to_ripe_stat(website_string: str) -> str:
    """
    Add link to checker at stat.ripe.net for a domain
    """

    url = make_url(website_string)
    domain = checker.validate_domain(url)
    resolved_ip = checker.convert_domain_to_ip(domain)

    if resolved_ip:
        return mark_safe(
            f"<a"
            f" target='_blank'"
            f" href='https://stat.ripe.net/{resolved_ip}'>"
            f"Check domain against RIPE stats"
            f"</a>"
        )


@register.filter()
def has_group(user, group_name) -> bool:
    """
    Check that a user has a specific group applied, and return
    either True if so, or False.
    """
    group = Group.objects.get(name=group_name)
    return True if group in user.groups.all() else False
