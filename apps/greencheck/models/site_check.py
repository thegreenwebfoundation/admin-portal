from dataclasses import dataclass

from django.utils import timezone

from ..choices import GreenlistChoice

@dataclass
class SiteCheck:
    """
    A representation of the Sitecheck object from the PHP app.
    We use it as a basis for logging to the Greencheck, but also maintaining
    our green_domains tables.
    """

    url: str
    ip: str
    data: bool
    green: bool
    hosting_provider_id: int
    checked_at: str
    match_type: str
    match_ip_range: int
    cached: bool


    @classmethod
    def green_sitecheck_by_carbon_txt(cls, domain,  carbon_txt):
        """
        Return a SiteCheck object, that has been marked as green by
        looking matching to a valid provider carbon.txt
        """
        return cls(
            url=domain,
            ip=None,
            data=True,
            green=True,
            hosting_provider_id=carbon_txt.provider_id,
            match_type=GreenlistChoice.CARBONTXT.value,
            match_ip_range=None,
            cached=False,
            checked_at=timezone.now(),
        )


    @classmethod
    def green_sitecheck_by_ip_range(cls, domain, ip_address, ip_match):
        """
        Return a SiteCheck object, that has been marked as green by
        looking up against an IP range
        """
        return cls(
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

    @classmethod
    def green_sitecheck_by_asn(cls, domain, ip_address, matching_asn):
        """
        Return a SiteCheck object, that has been marked as green by
        looking up against an IP range
        """
        return cls(
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

    @classmethod
    def grey_sitecheck(cls, domain, ip_address):
        """
        Return a SiteCheck object, that has been marked as grey
        for failure to match either by carbon.txt, ASN or IP.
        """
        return cls(
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
