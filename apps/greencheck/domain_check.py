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
import socket
import logging
from .models import GreencheckASN, GreencheckIp

from . import legacy_workers
from ipwhois.asn import IPASN
from ipwhois.net import Net
import ipaddress
from django.utils import timezone

logger = logging.getLogger(__name__)


class GreenDomainChecker:
    """
    The checking class. Used to run a check against a domain, to find the
    matching SiteCheck result, that we might log.
    """

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
    ) -> ipaddress.IPv4Network or ipaddress.IPv6Network:
        """
        Accepts a domain name or IP address, and returns an IPV4 or IPV6
        address
        """
        ip_string = socket.gethostbyname(domain)
        return ipaddress.ip_address(ip_string)

    def check_domain(self, domain: str):
        """
        Accept a domain name and return the either a GreenDomain Object,
        or the best matching IP range forip address it resolves to.
        """

        ip_address = self.convert_domain_to_ip(domain)

        ip_match = self.check_for_matching_ip_ranges(ip_address)
        if ip_match:

            check = legacy_workers.SiteCheck(
                url=domain,
                ip=str(ip_address),
                data=True,
                green=True,
                hosting_provider_id=ip_match.hostingprovider.id,
                match_type="IP",
                match_ip_range=ip_match.id,
                cached=False,
                checked_at=timezone.now(),
            )
            return check

        matching_asn = self.check_for_matching_asn(ip_address)
        logger.debug(f"matching_asn: {matching_asn}")
        if matching_asn:
            return legacy_workers.SiteCheck(
                url=domain,
                ip=str(ip_address),
                data=True,
                green=True,
                hosting_provider_id=matching_asn.hostingprovider.id,
                match_type="ASN",
                match_ip_range=matching_asn.id,
                cached=False,
                checked_at=timezone.now(),
            )

        return legacy_workers.SiteCheck(
            url=domain,
            ip=str(ip_address),
            data=False,
            green=False,
            hosting_provider_id=None,
            match_type=None,
            match_ip_range=None,
            cached=False,
            checked_at=timezone.now(),
        )

    def check_for_matching_ip_ranges(self, ip_address):
        """
        Look up the IP ranges that include this IP address, and return
        a list of IP ranges, ordered by smallest, most precise range first.
        """
        gc = GreencheckIp.objects.all().first()

        ip_matches = GreencheckIp.objects.filter(
            ip_end__gte=ip_address, ip_start__lte=ip_address,
        )
        # order matches by ascending range size
        return ip_matches.first()

    def check_for_matching_asn(self, ip_address):
        """
        Return the Green ASN that this IP address 'belongs' to.
        """
        asn = self.asn_from_ip(ip_address)
        return GreencheckASN.objects.filter(asn=asn).first()

