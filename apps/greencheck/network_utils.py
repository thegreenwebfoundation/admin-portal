import typing
import socket
import logging
import ipaddress
import urllib
import tld

from ipwhois.net import Net
from ipwhois.asn import IPASN

logger = logging.getLogger(__name__)

def validate_domain(url) -> typing.Union[str, None]:
    """
    Attempt to clean the provided url, and pull
    return the domain, or ip address
    """

    try:
        fetched_tld = tld.get_tld(url, fix_protocol=True)
        has_valid_tld = tld.is_tld(fetched_tld)
        if has_valid_tld:
            # note: we fetch this "as an object" this time
            res = tld.get_tld(url, fix_protocol=True, as_object=True)
            return res.parsed_url.netloc
    except tld.exceptions.TldDomainNotFound:
        pass

    # not a domain, try ip address, ending early if not
    try:
        ipaddress.ip_address(url)
    except ValueError:
        # not an ip address either, return an empty result
        return None

    parsed_url = urllib.parse.urlparse(url)
    if not parsed_url.netloc:
        # add the //, so that our url reading code
        # parses it properly
        parsed_url = urllib.parse.urlparse(f"//{url}")
    return parsed_url.netloc

def asn_from_ip(ip_address):
    """
    Check the IP against the IP 2 ASN service provided by the
    Team Cymru IP to ASN Mapping Service
    https://ipwhois.readthedocs.io/en/latest/ASN.html#asn-origin-lookups
    """
    network = Net(ip_address)
    obj = IPASN(network)
    res = obj.lookup()
    return res["asn"]

def convert_domain_to_ip(
    domain
) -> typing.Union[ipaddress.IPv4Address, ipaddress.IPv6Address]:
    """
    Accepts a domain name or IP address, and returns an IPV4 or IPV6
    address, raising an exception if not resolution occurs.
    """

    # TODO: support multiple addresses being returned:
    # `getaddrinfo`` actually returns a list of possible addresses,
    # but our current code only assumes a domain would resolve to a single IP
    # address when we look up a domain.
    # Ideally we'd check that ALL the IP addresses resolved are within our
    # green IP ranges but until we know how much this impacts performance
    # we choose the first one.
    ip_info = socket.getaddrinfo(domain, None)

    # each item in the list is a tuple containing:

    # Address family (like socket.AF_INET for IPv4 or socket.AF_INET6 for IPv6)
    # Socket type (like socket.SOCK_STREAM for TCP or socket.SOCK_DGRAM for UDP)
    # Protocol (usually just 0)
    # Canonical name (an alias for the host, if applicable)
    # Socket address (a tuple containing the IP address and port number)

    ip_address_list = [
        # we are fetching the ip address in our socket address returned above
        ip[4][0]
        for ip in ip_info
    ]

    ip = ipaddress.ip_address(ip_address_list[0])
    logger.debug(ip)

    if ip:
        return ip

    raise ipaddress.AddressValueError(f"Unable to convert domain to IP: {domain}")

def order_ip_range_by_size(ip_matches):
    """
    Returns a queryset's worth of Green IP Ranges, ordered
    from smallest range first, as a list.
    This allows resellers to show up in a supply chain check
    on a site.
    """
    range_list = [
        {"ip_range": ip_range, "range_length": ip_range.ip_range_length()}
        for ip_range in ip_matches
    ]

    # now sort by the length, in ascending order
    ascending_ip_ranges = sorted(
        range_list, key=lambda ip_obj: ip_obj.get("range_length")
    )

    # sort to return the smallest first
    return [obj["ip_range"] for obj in ascending_ip_ranges]

