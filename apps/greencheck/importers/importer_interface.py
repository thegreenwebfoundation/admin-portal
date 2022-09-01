import ipaddress
import re
import logging
import rich

from typing import Protocol, runtime_checkable, Union

from apps.greencheck.models import GreencheckIp, GreencheckASN
from apps.accounts.models import Hostingprovider

logger = logging.getLogger(__name__)


@runtime_checkable
class Importer(Protocol):
    def fetch_data_from_source(self) -> list:
        """
        Fetches the data, and returns a data structure for parsing
        with `parse_to_list`
        """
        raise NotImplementedError

    def parse_to_list(self) -> list:
        """
        Returns a list of either strings that can be parsed as AS numbers
        or IP networks
        """
        raise NotImplementedError


class BaseImporter:
    hosting_provider: Hostingprovider

    def is_ip_range(self, address: Union[str, tuple]) -> Union[tuple, bool]:
        """
        Check if "address" is a usable ip range, and return the tuple containing
        the required ip addresses, ready for importing as an ip range
        """
        # return early if not a tuple we can parse
        if not isinstance(address, tuple):
            return

        first_ip = ipaddress.ip_address(address[0])
        last_ip = ipaddress.ip_address(address[-1])
        if first_ip and last_ip:
            return address

    def is_ip_network(self, address: Union[str, tuple]):
        """
        Chck that "address" is a string we can parse to an ip network,
        ready for saving as an ip range.
        """
        # return early if not a string we can parse
        if not isinstance(address, str):
            return

        # this looks an AS number return early
        if address.startswith("AS"):
            return

        try:
            network = ipaddress.ip_network(address)
        except ValueError:
            logger.exception(
                (
                    f"Value for address: {address} has an invalid structure. "
                    "Must be IPv4 or IPv6 with subnetmask (101.102.103.104/27) "
                    "or AS number (AS123456)."
                )
            )
            return

        if network:
            return network

    def is_as_number(self, address: Union[str, tuple]) -> Union[str, bool]:
        """
        Check that "address" is a string suitable for saving as a AS number
        """
        # return early if not a string we can parse
        if not isinstance(address, str):
            return

        if address.startswith("AS"):
            return address

    def process_addresses(self, list_of_addresses: list):
        count_asn = 0
        count_ip = 0

        # Determine the type of address (IPv4, IPv6 or ASN) for
        # address in list_of_addresses:
        try:
            for address in list_of_addresses:

                if self.is_ip_range(address):
                    # address looks like an IPv4 or IPv6 range
                    self.save_ip(address)
                    count_ip += 1
                    continue

                if self.is_ip_network(address):
                    # address looks like IPv4 or IPv6 network
                    network = ipaddress.ip_network(address)
                    self.save_ip((network[1], network[-1]))
                    count_ip += 1
                    continue

                if self.is_as_number(address):
                    # address is ASN
                    self.save_asn(address)
                    count_asn += 1
                    continue

            return (
                f"Processing complete. Added {count_asn} ASN's and {count_ip} IP "
                "ranges (either IPv4 and/or IPv6)"
            )
        except ValueError:
            return (
                f"An error occurred while adding new entries. Added {count_asn} AS "
                f"numbers and {count_ip} ip ranges (either IPv4 and/or IPv6)"
            )
        except Exception as e:
            logger.exception("Something really unexpected happened. Aborting")
            logger.exception(e)
            return (
                "An error occurred while adding new entries. "
                f"Added {count_asn} ASN's and {count_ip} IP's "
                "(either IPv4 and/or IPv6)"
            )

    def save_asn(self, address: str):
        

        gc_asn, created = GreencheckASN.objects.update_or_create(
            active=True, 
            asn=int(address.replace("AS", "")),
            hostingprovider=self.hosting_provider
        )
        gc_asn.save()  # Save the newly created or updated object

        if created:
            # Only log and return when a new object was created
            logger.debug(gc_asn)
            return gc_asn

    def save_ip(self, address):
        if isinstance(address, tuple):
            start_address = ipaddress.ip_address(address[0])
            ending_address = ipaddress.ip_address(address[1])
        elif isinstance(address, str):
            network = ipaddress.ip_network(address)

            start_address = network[1]
            ending_address = network[-1]

        gc_ip, created = GreencheckIp.objects.update_or_create(
            active=True,
            ip_start=start_address,
            ip_end=ending_address,
            hostingprovider=self.hosting_provider,
        )
        gc_ip.save()  # Save the newly created or updated object

        if created:
            # Only log and return when a new object was created
            logger.debug(gc_ip)
            return gc_ip
