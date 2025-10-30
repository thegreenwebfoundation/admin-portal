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

import ipwhois
from ipwhois.exceptions import (
    ASNLookupError,
    ASNOriginLookupError,
    ASNParseError,
    ASNRegistryError,
    IPDefinedError,
)

from .models import GreenDomain, SiteCheck
from .network_utils import asn_from_ip, convert_domain_to_ip, order_ip_range_by_size
from ..accounts.models import ProviderCarbonTxt

logger = logging.getLogger(__name__)

UNRESOLVED_ADDRESS = "0.0.0.0"

class GreenDomainChecker:
    """
    The checking class. Used to run a check against a domain, to find the
    matching SiteCheck result, that we might log.
    """


    def perform_full_lookup(self, domain: str, refresh_carbon_txt_cache : bool = False) -> GreenDomain:
        """
        Return a Green Domain object from doing a lookup.
        """
        from .models import GreenDomain

        res = self.check_domain(domain, refresh_carbon_txt_cache=refresh_carbon_txt_cache)

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

        An extended greencheck ALWAYS refreshes the carbon.txt cache to make sure
        that the returned result is accurate.
        """
        try:
            ip_address = convert_domain_to_ip(domain_to_check)
        except (socket.gaierror, ipaddress.AddressValueError) as err:
            logger.warning(f"Unable to lookup domain: {domain_to_check} - error: {err}")
        except Exception as err:
            logger.warning(f"Unable to lookup domain: {domain_to_check} - error: {err}")

        # fetch our sitecheck object
        site_check = self.check_domain(domain_to_check, refresh_carbon_txt_cache=True)
        # fetch our GreendDomain object
        green_domain = self.perform_full_lookup(domain_to_check, refresh_carbon_txt_cache=True)

        # carry out our extended whois lookup
        whois_lookup = ipwhois.IPWhois(ip_address)
        rdap = whois_lookup.lookup_rdap(depth=1)

        return {
            "domain": domain_to_check,
            "green_domain": green_domain,
            "site_check": site_check,
            "whois_info": rdap,
        }


    def check_domain(self, domain: str, refresh_carbon_txt_cache : bool = False) -> SiteCheck:
        """
        Accept a domain name and return either a GreenDomain Object,
        the best matching IP range for the ip address it resolves to,
        or a 'grey' Sitecheck
        """
        # First, check for a green provider match by carbon_txt
        if carbon_txt := self.check_for_matching_carbon_txt(domain, refresh_carbon_txt_cache):
                return SiteCheck.green_sitecheck_by_carbon_txt(domain, carbon_txt)

        # If this fails, attempt to resolve the IP address for the domain
        if ip_address := self.ip_for_domain(domain):
            # If we get a matching IP, check whether it matches the known ranges for a green provider
            if ip_match := self.check_for_matching_ip_ranges(ip_address):
                return SiteCheck.green_sitecheck_by_ip_range(domain, ip_address, ip_match)

            # If this fails, fallback to check whether it matches a known ASN for a green provider
            if matching_asn := self.check_for_matching_asn(ip_address):
                return SiteCheck.green_sitecheck_by_asn(domain, ip_address, matching_asn)

        # otherwise, we return a grey rseult.
        if not ip_address:
            ip_address = UNRESOLVED_ADDRESS
        return SiteCheck.grey_sitecheck(domain, ip_address)

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
        ordered_matches = order_ip_range_by_size(ip_matches)

        if ordered_matches:
            return ordered_matches[0]

    def check_for_matching_carbon_txt(self, domain, refresh_carbon_txt_cache):
        if carbon_txt := ProviderCarbonTxt.find_for_domain(domain, refresh_cache=refresh_carbon_txt_cache):
            if carbon_txt.is_valid and carbon_txt.provider.counts_as_green:
                return carbon_txt

    def check_for_matching_asn(self, ip_address):
        """
        Return the Green ASN that this IP address 'belongs' to.
        """
        from .models import GreencheckASN

        try:
            asn_result = asn_from_ip(ip_address)

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

    def ip_for_domain(self, domain):
        try:
            ip_address = convert_domain_to_ip(domain)
            return ip_address
        except (ipaddress.AddressValueError, socket.gaierror):
            pass
        except Exception as err:
            logger.warning(
                f"Unexpected exception looking up: {domain} - error was: {err}"
            )
            pass
