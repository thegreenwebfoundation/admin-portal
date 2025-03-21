"""
A python implementation of the domain checker powering the previous php based versions
of the Greencheck API.

This follows largely the same approach:

1. take a domain or ip address
2. convert to ip address if need be.
3. check for existing match in the ip ranges, choosing the smallest range
   that matches the query
4. if no match, look up ASN from provided ip address
5. check against registered ASNs
6. if no matches left, report grey
"""

import ipaddress
import logging
import socket
import typing
import urllib
from urllib.parse import urlparse

import dns.resolver
import httpx
import ipwhois
import tld
from django.utils import timezone
from ipwhois.asn import IPASN
from ipwhois.exceptions import (
    ASNLookupError,
    ASNOriginLookupError,
    ASNParseError,
    ASNRegistryError,
    IPDefinedError,
)
from ipwhois.net import Net

from .choices import GreenlistChoice
from .models import GreenDomain, SiteCheck
from ..accounts.models import LinkedDomain, LinkedDomainState

logger = logging.getLogger(__name__)


class GreenDomainChecker:
    """
    The checking class. Used to run a check against a domain, to find the
    matching SiteCheck result, that we might log.
    """

    def validate_domain(self, url) -> typing.Union[str, None]:
        """
        Attempt to clean the provided url, and pull
        return the domain, or ip address
        """

        try:
            fetched_tld = tld.get_tld(url, fix_protocol=True)
            has_valid_tld = tld.is_tld(fetched_tld)
        except tld.exceptions.TldDomainNotFound:
            return ""

        # looks like a domain
        if has_valid_tld:
            # note: we fetch this "as an object" this time
            res = tld.get_tld(url, fix_protocol=True, as_object=True)
            return res.parsed_url.netloc

        # not a domain, try ip address, ending early if not
        try:
            ipaddress.ip_address(url)
        except ValueError:
            # not an ip address either, return an empty result
            return ""

        parsed_url = urllib.parse.urlparse(url)
        if not parsed_url.netloc:
            # add the //, so that our url reading code
            # parses it properly
            parsed_url = urllib.parse.urlparse(f"//{url}")
        return parsed_url.netloc

    def perform_full_lookup(self, domain: str) -> GreenDomain:
        """
        Return a Green Domain object from doing a lookup.
        """
        from .models import GreenDomain

        res = self.check_domain(domain)

        if not res.green:
            return GreenDomain.grey_result(domain=res.url)

        # return a domain result, but don't save it,
        # as persisting it is handled asynchronously
        # by another worker, and logged to both the greencheck
        # table and this 'cache' table
        return GreenDomain.from_sitecheck(res)

    def extended_domain_info_lookup(self, domain_to_check: str) -> typing.Dict:
        """
        Accept an domain or IP address, and return extended information
        about it, like extended whois data, and any relevant sitecheck
        or green domain objects.
        """
        try:
            ip_address = self.convert_domain_to_ip(domain_to_check)
        except (socket.gaierror, ipaddress.AddressValueError) as err:
            logger.warning(f"Unable to lookup domain: {domain_to_check} - error: {err}")
        except Exception as err:
            logger.warning(f"Unable to lookup domain: {domain_to_check} - error: {err}")

        # fetch our sitecheck object
        site_check = self.check_domain(domain_to_check)
        # fetch our GreendDomain object
        green_domain = self.perform_full_lookup(domain_to_check)

        # carry out our extended whois lookup
        whois_lookup = ipwhois.IPWhois(ip_address)
        rdap = whois_lookup.lookup_rdap(depth=1)

        return {
            "domain": domain_to_check,
            "green_domain": green_domain,
            "site_check": site_check,
            "whois_info": rdap,
        }

    def asn_from_ip(self, ip_address):
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
        self, domain
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

    def green_sitecheck_by_ip_range(self, domain, ip_address, ip_match):
        """
        Return a SiteCheck object, that has been marked as green by
        looking up against an IP range
        """
        return SiteCheck(
            url=domain,
            ip=str(ip_address),
            data=True,
            green=True,
            hosting_provider_id=ip_match.hostingprovider.id,
            match_type=GreenlistChoice.IP.value,
            match_ip_range=ip_match.id,
            cached=False,
            checked_at=timezone.now(),
        )

    def green_sitecheck_by_asn(self, domain, ip_address, matching_asn):
        return SiteCheck(
            url=domain,
            ip=str(ip_address),
            data=True,
            green=True,
            hosting_provider_id=matching_asn.hostingprovider.id,
            match_type=GreenlistChoice.ASN.value,
            match_ip_range=matching_asn.id,
            cached=False,
            checked_at=timezone.now(),
        )

    def grey_sitecheck(
        self,
        domain,
        ip_address,
    ):
        return SiteCheck(
            url=domain,
            ip=str(ip_address),
            data=False,
            green=False,
            hosting_provider_id=None,
            match_type=GreenlistChoice.IP.value,
            match_ip_range=None,
            cached=False,
            checked_at=timezone.now(),
        )

    def check_via_linked_domain(self, domain):
        """
        Check against domains linked by providers using carbon.txt
        """
        try:
            linked_domain = LinkedDomain.objects.get(domain=domain, state=LinkedDomainState.APPROVED)
            provider = linked_domain.provider
            if provider and provider.counts_as_green:
                return linked_domain
        except LinkedDomain.DoesNotExist:
            return None

    def green_sitecheck_by_linked_domain(
        self, domain: str, matching_linked_domain: LinkedDomain
    ):
        """
        Return a green site check, based the information we
        are showing via linked domains for a provider
        """
        return SiteCheck(
            url=domain,
            ip=None,
            data=True,
            green=True,
            hosting_provider_id=matching_linked_domain.provider_id,
            # NOTE: we use WHOIS for now, as a way to decouple
            # an expensive and risky migration from the rest of
            # this carbon.txt work. See this issue for more:
            # https://github.com/thegreenwebfoundation/admin-portal/issues/198
            # match_type=GreenlistChoice.CARBONTXT.value,
            match_type=GreenlistChoice.WHOIS.value,
            match_ip_range=None,
            cached=False,
            checked_at=timezone.now(),
        )

    def check_domain(self, domain: str) -> SiteCheck:
        """
        Accept a domain name and return either a GreenDomain Object,
        the best matching IP range for the ip address it resolves to,
        or a 'grey' Sitecheck
        """
        UNRESOLVED_ADDRESS = "0.0.0.0"

        if linked_domain := self.check_via_linked_domain(domain):
            return self.green_sitecheck_by_linked_domain(domain, linked_domain)

        try:
            ip_address = self.convert_domain_to_ip(domain)
        except (ipaddress.AddressValueError, socket.gaierror):
            ip_address = UNRESOLVED_ADDRESS
            return self.grey_sitecheck(domain, ip_address)
        except Exception as err:
            logger.warning(
                f"Unexpected exception looking up: {domain} - error was: {err}"
            )
            ip_address = UNRESOLVED_ADDRESS
            return self.grey_sitecheck(domain, ip_address)

        if ip_match := self.check_for_matching_ip_ranges(ip_address):
            return self.green_sitecheck_by_ip_range(domain, ip_address, ip_match)

        if matching_asn := self.check_for_matching_asn(ip_address):
            return self.green_sitecheck_by_asn(domain, ip_address, matching_asn)

        # otherwise, return a 'grey' result
        return self.grey_sitecheck(domain, ip_address)

    def check_for_matching_ip_ranges(self, ip_address):
        """
        Look up the IP ranges that include this IP address, and return
        a list of IP ranges, ordered by smallest, most precise range first.
        """
        from .models import GreencheckIp

        ip_matches = GreencheckIp.objects.filter(
            ip_end__gte=ip_address, ip_start__lte=ip_address, active=True
        )

        # order matches by ascending range size
        # we can't do this in the database because we need to work out the
        # size of the Ip ranges in order to order them properly
        ordered_matches = self.order_ip_range_by_size(ip_matches)

        if ordered_matches:
            return ordered_matches[0]

    def check_for_matching_asn(self, ip_address):
        """
        Return the Green ASN that this IP address 'belongs' to.
        """
        from .models import GreencheckASN

        try:
            asn_result = self.asn_from_ip(ip_address)

        except (
            ASNLookupError,
            ASNParseError,
            ASNRegistryError,
            ASNOriginLookupError,
            IPDefinedError,
        ) as ex:
            logger.warning(
                f"Unable to parse ASN for IP: {ip_address} - error type: {type(ex).__name__} {ex}"
            )
            return False
        except Exception as err:
            logger.exception(err)
            return False

        if isinstance(asn_result, int):
            return GreencheckASN.objects.filter(asn=asn_result, active=True).first()

        if asn_result == "NA" or asn_result is None:
            logger.info("Received a result we can't match to an ASN. Skipping")
            # we can't process this IP address. Skip it.
            return False

        # we have a string containing more than one ASN.
        # look them up, and return the first green one
        asns = asn_result.split(" ")
        for asn in asns:
            asn_match = GreencheckASN.objects.filter(asn=asn, active=True)
            if asn_match:
                # we have a match, return the result
                return asn_match.first()

    def grey_urls_only(self, urls_list, queryset) -> list:
        """
        Accept a list of domain names, and a queryset of checked green
        domain objects, and return a list of only the grey domains.
        """
        green_list = [domain_object.url for domain_object in queryset]

        return [url for url in urls_list if url not in green_list]

    def build_green_greylist(self, grey_list: list, green_list) -> list:
        """
        Create a list of green and grey domains, to serialise and deliver.
        """
        from .models import GreenDomain

        grey_domains = []

        for domain in grey_list:
            gp = GreenDomain.grey_result(domain=domain)
            grey_domains.append(gp)

        evaluated_green_queryset = green_list[::1]

        return evaluated_green_queryset + grey_domains

    def order_ip_range_by_size(self, ip_matches):
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

