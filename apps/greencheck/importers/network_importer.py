import ipaddress
import logging
from typing import Union

from apps.accounts.models import Hostingprovider
from apps.greencheck.models import GreencheckASN, GreencheckIp

logger = logging.getLogger(__name__)


def is_ip_network(address: str) -> bool:
    """
    Check that "address" is a string we can parse to an ip network,
    ready for saving as an ip range.
    Where we get addresses like '104.21.2.192/24'
    we want to raise an exception rather than try to fix
    """

    # exit early if we do not have slash dividing
    # the network address / network prefix
    if "/" not in address:
        return False

    try:
        ipaddress.ip_network(address)
        return True
    except ValueError:
        return False


def ip_address_without_subnet_mask(address: str) -> str:
    """
    Accept an IP address, and return it without
    the subnet mask if it was added
    """
    # sometimes IP addresses are provided including
    # a network prefix, like 123.123.123.123/24.
    # Python rejects these as invalid IP addresses, because
    # adding the /24 prefix means this could be any address
    # from 123.123.123.0 or 123.123.123.255
    #
    # We currently assume that if someone is providing a full
    # address like this PLUS a prefix, they mean the ip address,
    # not the whole network

    if "/" in address:
        return address.split("/")[0]

    # otherwise return our address as normal
    return address


def is_ip_range(address: Union[str, tuple]) -> bool:
    """
    Check if "address" is a valid ip range.
    """
    # return early if not a tuple we can parse
    if not isinstance(address, (tuple, list)):
        return False

    first_ip, second_ip = address

    try:
        return bool(ipaddress.ip_address(first_ip) and ipaddress.ip_address(second_ip))

    except ValueError as ex:
        logger.warning(
            f"Could not extract an IP address pair from address: {address}. Error: {ex}"
        )


def is_asn(address: Union[str, tuple]) -> bool:
    """
    Check that "address" is a string suitable for saving as an AS number
    """
    # return early if not a string we cacn parse
    if not isinstance(address, str):
        return False

    if not address.startswith("AS"):
        return False

    as_number = address.replace("AS", "")
    if as_number:
        try:
            int(as_number)
            return True
        except Exception as ex:
            logger.warning(
                f"Unable to turn find AS number in AS: {address}, exception was: {ex}"
            )

    return False


class NetworkImporter:
    """
    An importer designed to accept a list of IP Ranges or AS numbers and add
    them to the corresponding Provider
    """

    hosting_provider: Hostingprovider

    def __init__(self, provider):
        self.hosting_provider = provider

    def deactivate_ips(self) -> int:
        """
        Find all the active Green IPs associated with the provider,
        and deactivate them, ready to reactivate with the import
        """
        active_green_ips = self.hosting_provider.greencheckip_set.filter(active=True)
        return active_green_ips.update(active=False)

    def deactivate_asns(self) -> int:
        """
        Find all the active Green IPs associated with the provider,
        and deactivate them, ready to reactivate with the import
        """
        active_green_ips = self.hosting_provider.greencheckasn_set.filter(active=True)
        return active_green_ips.update(active=False)

    def save_asn(self, address: str):
        gc_asn, created = GreencheckASN.objects.update_or_create(
            asn=int(address.replace("AS", "")),
            hostingprovider=self.hosting_provider,
        )

        gc_asn.active = True
        gc_asn.save()

        if created:
            return (gc_asn, created)

        return (gc_asn, False)

    def save_ip(self, address, location=None):
        if is_ip_range(address):
            start_address = ipaddress.ip_address(address[0])
            ending_address = ipaddress.ip_address(address[1])
        elif is_ip_network(address):
            network = ipaddress.ip_network(address)
            start_address = network[0]
            ending_address = network[-1]

        gc_ip, created = GreencheckIp.objects.update_or_create(
            ip_start=start_address,
            ip_end=ending_address,
            hostingprovider=self.hosting_provider,
        )

        if location:
            gc_ip.location = location

        gc_ip.active = True
        gc_ip.save()

        if created:
            return (gc_ip, created)

        return (gc_ip, False)

    def process_addresses(self, list_of_addresses: list):
        green_asns = []
        green_ips = []
        created_green_ips = []
        created_asns = []

        # Determine the type of address (IPv4, IPv6 or ASN) for
        # address in list_of_addresses:
        try:
            for address in list_of_addresses:

                if is_ip_range(address):
                    # address looks like an IPv4 or IPv6 range
                    green_ip, created = self.save_ip(address)
                    if created:
                        created_green_ips.append(green_ip)
                    else:
                        green_ips.append(green_ip)
                    continue

                if is_ip_network(address):
                    # address looks like IPv4 or IPv6 network
                    # turn it to an ip_network object
                    network = ipaddress.ip_network(address)
                    green_ip, created = self.save_ip((network[0], network[-1]))

                    if created:
                        created_green_ips.append(green_ip)
                    else:
                        green_ips.append(green_ip)
                    continue

                if is_asn(address):
                    # address is ASN
                    green_asn, created = self.save_asn(address)
                    if created:
                        created_asns.append(green_asn)
                    else:
                        green_asns.append(green_asn)
                    continue

                logger.warning(f"Could not determine the type of address {address}")
            logger.info(
                f"Processing complete. Created {len(created_asns)} ASNs, and "
                f"{len(created_green_ips)} IP ranges. Updated {len(green_asns)} ASNs, "
                f"and {len(green_ips)} IP ranges. (either IPv4 and/or IPv6)"
            )
            return {
                "green_ips": green_ips,
                "green_asns": green_asns,
                "created_asns": created_asns,
                "created_green_ips": created_green_ips,
            }
        except ValueError:
            logger.warning("An error occurred while adding new entries")
            return {
                "green_ips": green_ips,
                "green_asns": green_asns,
                "created_asns": created_asns,
                "created_green_ips": created_green_ips,
            }
        except Exception as e:
            logger.exception("Something really unexpected happened. Aborting")
            logger.exception(e)
            return {
                "green_ips": green_ips,
                "green_asns": green_asns,
                "created_asns": created_asns,
                "created_green_ips": created_green_ips,
            }
