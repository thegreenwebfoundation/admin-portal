import logging
import socket
import urllib

from django import template
from django.contrib.auth.models import Group
from django.utils.safestring import mark_safe

from apps.greencheck import domain_check

logger = logging.getLogger(__name__)
register = template.Library()
checker = domain_check.GreenDomainChecker()
console = logging.StreamHandler()


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
    Add link to checker at stat.ripe.net for a domain.
    Returns an empty string if the lookup does not work
    """

    url = make_url(website_string)
    domain = checker.validate_domain(url)

    try:
        resolved_ip = checker.convert_domain_to_ip(domain)
    except socket.gaierror as err:
        logger.warning(f"Could not resolve domain {domain}: error was {err}")
        resolved_ip = None
    except Exception as err:
        logger.exception(f"Unexpected error looking up {domain}: error was {err}")
        resolved_ip = None

    if resolved_ip:
        return mark_safe(
            f"<a"
            f" target='_blank'"
            f" href='https://stat.ripe.net/{resolved_ip}'>"
            f"Check domain against RIPE stats"
            f"</a>"
        )

    # Return an empty string as a graceful fallback to avoid
    # having `None` cast into a string saying "None"
    # in our template
    return ""


@register.filter()
def has_group(user, group_name) -> bool:
    """
    Check that a user has a specific group applied, and return
    either True if so, or False.
    """
    group = Group.objects.filter(name=group_name)

    if not group:
        return False

    return True if group[0] in user.groups.all() else False
