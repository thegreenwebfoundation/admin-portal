import typing
import logging
import socket
import ipaddress

import ipwhois

from .network_utils import convert_domain_to_ip
from .models import GreenDomain
from .domain_check import GreenDomainChecker

logger = logging.getLogger(__name__)


logger = logging.getLogger(__name__)

def extended_domain_info_lookup(domain_to_check: str) -> typing.Dict:
    """
    Accept an domain or IP address, and return extended information
    about it, like extended whois data, and any relevant sitecheck
    or green domain objects.

    An extended greencheck ALWAYS refreshes the carbon.txt cache to make sure
    that the returned result is accurate.
    """
    checker = GreenDomainChecker()
    try:
        ip_address = convert_domain_to_ip(domain_to_check)
    except (socket.gaierror, ipaddress.AddressValueError) as err:
        logger.warning(f"Unable to lookup domain: {domain_to_check} - error: {err}")
    except Exception as err:
        logger.warning(f"Unable to lookup domain: {domain_to_check} - error: {err}")

    # fetch our sitecheck object
    site_check = checker.check_domain(domain_to_check, refresh_carbon_txt_cache=True)
    # fetch our GreendDomain object
    green_domain = GreenDomain.green_domain_for(domain_to_check, skip_cache=True)

    # carry out our extended whois lookup
    whois_lookup = ipwhois.IPWhois(ip_address)
    rdap = whois_lookup.lookup_rdap(depth=1)

    return {
        "domain": domain_to_check,
        "green_domain": green_domain,
        "site_check": site_check,
        "whois_info": rdap,
    }

