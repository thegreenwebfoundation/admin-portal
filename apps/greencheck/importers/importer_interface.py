import ipaddress
import re
import logging

from typing import Protocol, runtime_checkable

from apps.greencheck.models import GreencheckIp, GreencheckASN
from apps.accounts.models import Hostingprovider

logger = logging.getLogger(__name__)

@runtime_checkable
class Importer(Protocol):
    def fetch_data_from_source(cls) -> list:
        raise NotImplementedError

    def parse_to_list(cls) -> list:
        raise NotImplementedError

class BaseImporter():
    hosting_provider_id:int

    def process_addresses(cls, list_of_addresses: list):
        count_asn = 0
        count_ip = 0
        
        # Determine the type of address (IPv4, IPv6 or ASN)for address in list_of_addresses:
        try:
            for address in list_of_addresses:
                if re.search("(AS)[0-9]+$", address):
                    # Address is ASN
                    cls.save_asn(cls, address)
                    count_asn += 1
                elif isinstance(
                    ipaddress.ip_network(address),
                    (ipaddress.IPv4Network, ipaddress.IPv6Network),
                ):
                    # Address is IPv4 or IPv6
                    cls.save_ip(cls, address)
                    count_ip += 1
            
            return f"Processing complete. Added {count_asn} ASN's and {count_ip} IP's (either IPv4 and/or IPv6)"
        except ValueError:
            logger.exception(
                "Value has invalid structure. Must be IPv4 or IPv6 with subnetmask (101.102.103.104/27) or AS number (AS123456)."
            )
            return f"An error occurred while adding new entries. Added {count_asn} ASN's and {count_ip} IP's (either IPv4 and/or IPv6)"
        except Exception as e:
            logger.exception("Something really unexpected happened. Aborting")
            logger.exception(e)
            return f"An error occurred while adding new entries. Added {count_asn} ASN's and {count_ip} IP's (either IPv4 and/or IPv6)"

    def save_asn(cls, address: str):
        hoster = Hostingprovider.objects.get(
            pk=cls.hosting_provider_id
        )

        gc_asn, created = GreencheckASN.objects.update_or_create(
            active=True, asn=int(address.replace("AS", "")), hostingprovider=hoster
        )
        gc_asn.save()  # Save the newly created or updated object

        if created:
            # Only log and return when a new object was created
            logger.debug(gc_asn)
            return gc_asn

    def save_ip(cls, address: str):
        # Convert to IPv4 network with it's respective range
        network = ipaddress.ip_network(address)
        hoster = Hostingprovider.objects.get(
            pk=cls.hosting_provider_id
        )

        gc_ip, created = GreencheckIp.objects.update_or_create(
            active=True, ip_start=network[1], ip_end=network[-1], hostingprovider=hoster
        )
        gc_ip.save()  # Save the newly created or updated object

        if created:
            # Only log and return when a new object was created
            logger.debug(gc_ip)
            return gc_ip