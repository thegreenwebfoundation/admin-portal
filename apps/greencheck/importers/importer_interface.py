import ipaddress
import re
import logging
import pdb

from typing import Protocol, runtime_checkable, List
from django.db import transaction

from apps.greencheck.models import GreencheckIp, GreencheckASN
from apps.accounts.models import Hostingprovider

logger = logging.getLogger(__name__)


@runtime_checkable
class Importer(Protocol):
    def fetch_data_from_source(cls) -> list:
        raise NotImplementedError

    def parse_to_list(cls) -> list:
        raise NotImplementedError


class BaseImporter:
    hosting_provider_id: int

    # @transaction.atomic
    def process_addresses(cls, list_of_addresses: list):
        count_ip = 0
        count_asn = 0

        try:
            # Extract ASN and IP values from the generic list
            regex = re.compile("(AS)[0-9]+$")
            asn_list = list(filter(regex.match, list_of_addresses))
            ip_list = list(set(list_of_addresses) - set(asn_list))

            # ASN list preperation: formatting
            asn_list = list(map(int, map(lambda x: x.replace("AS", ""), asn_list)))
            count_asn = cls.update_asn(cls, asn_list)

            # IP list preperation: type checking
            ip_list = list(
                filter(
                    lambda x: isinstance(
                        ipaddress.ip_network(x),
                        (ipaddress.IPv4Network, ipaddress.IPv6Network),
                    ),
                    ip_list,
                )
            )
            count_ip = cls.update_ip(cls, ip_list)

            return f"Processing complete. Updated {count_asn} ASN's and {count_ip} IP's (IPv4 and/or IPv6)"
        except ValueError:
            logger.exception(
                "Value has invalid structure. Must be IPv4 or IPv6 with subnetmask (101.102.103.104/27) or AS number (AS123456)."
            )
            return f"An error occurred while adding new entries. Updated {count_asn} ASN's and {count_ip} IP's (IPv4 and/or IPv6)"
        except Exception as e:
            logger.exception("Something really unexpected happened. Aborting")
            logger.exception(e)
            return f"An error occurred while adding new entries. Updated {count_asn} ASN's and {count_ip} IP's (IPv4 and/or IPv6)"

    def update_asn(cls, active_networks: List[int]) -> int:
        active_networks = list(set(active_networks))  # extract unique values
        updated_networks = 0

        logger.debug("Running atomic database transaction. Altered AS numbers:")
        with transaction.atomic():
            # Retrieve all ASN entries assosiated with this hosting provider
            hosting_provider = Hostingprovider.objects.get(pk=cls.hosting_provider_id)
            entries = GreencheckASN.objects.select_for_update().filter(
                hostingprovider=hosting_provider
            )

            # Iterate database entries
            for entry in entries:
                if entry.asn in active_networks:
                    active_networks.pop(active_networks.index(entry.asn))
                    entry.active = True
                    entry.save()

                    updated_networks += 1
                    logger.debug(entry)
                elif entry.active == True:
                    entry.active = False
                    entry.save()

                    updated_networks += 1
                    logger.debug(entry)

            # Iterate remaining list items (that are not in the database)
            if active_networks:
                for asn_network in active_networks:
                    entry, created = GreencheckASN.objects.update_or_create(
                        active=True, asn=asn_network, hostingprovider=hosting_provider
                    )
                    entry.save()

                    if created:
                        logger.debug(entry)

        return updated_networks

    def update_ip(cls, active_networks: List[str]) -> int:
        updated_networks = 0

        # Convert networks (xxx.xxx.xxx.xxx/yy) to a
        # start and end ip address
        tmp_list = []
        for ip_network in active_networks:
            network = ipaddress.ip_network(ip_network)
            tmp_list.append((str(network[1]), str(network[-1])))
        active_networks = list(set(tmp_list))

        logger.debug("Running atomic database transaction. Altered IP ranges:")
        with transaction.atomic():
            # Retrieve all IP(v4 and v6) entries assosiated to this hosting provider
            hosting_provider = Hostingprovider.objects.get(pk=cls.hosting_provider_id)
            entries = GreencheckIp.objects.select_for_update().filter(
                hostingprovider=hosting_provider
            )

            # Iterate database entries
            for entry in entries:
                if (entry.ip_start, entry.ip_end) in active_networks:
                    active_networks.pop(
                        active_networks.index((entry.ip_start, entry.ip_end))
                    )
                    entry.active = True
                    entry.save()

                    updated_networks += 1
                    logger.debug(entry)
                elif entry.active == True:
                    entry.active = False
                    entry.save()

                    updated_networks += 1
                    logger.debug(entry)

            # Iterate remaining list items (that are not in the database)
            if active_networks:
                for ip_network in active_networks:
                    entry, created = GreencheckIp.objects.update_or_create(
                        active=True,
                        ip_start=ip_network[0],
                        ip_end=ip_network[1],
                        hostingprovider=hosting_provider,
                    )
                    entry.save()

            if created:
                logger.debug(entry)

        return updated_networks
