import urllib
from django import template

import logging

register = template.Library()

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


# def link_to_ripe_stat(website_string: str) -> str:
#     """
#     Add link to RIPE checker
#     """

#     logger.debug(f"RECIEVED THIS: {str}")

