import ipaddress
import re
import logging

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
        """
        General function that processes all types of addresses (IPv4, IPv6 and ASN).

        The list that is given to this function is considered a list of active networks
        and the process that is taking place is changing the state of these addresses
        in the database in terms of their state.

        Addresses in the list will be set as active, and other addresses in the database
        will be set to inactive.
        """
        # TODO: Add docstring
        count_ip = 0
        count_asn = 0

        try:
            # Prepare and run ASN update
            regex = re.compile("(AS)[0-9]+$")
            asn_list = list(set(filter(regex.match, list_of_addresses)))
            count_asn = cls.update_asn(cls, asn_list)

            # Prepare and run IP update
            ip_list = list(set(list_of_addresses) - set(asn_list))
            ip_list = list(
                filter(
                    lambda x: isinstance(
                        ipaddress.ip_network(x),
                        (ipaddress.IPv4Network, ipaddress.IPv6Network),
                    ),
                    ip_list,
                )
            )  # Type checking
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

    def update_asn(cls, active_networks: List[str]) -> int:
        """
        General function that updates a hostingprovider's ASN networks.
        Under "networks" in this case, it is understood that it needs to have a format 
        similar to for example: AS12345.
        Return: int, number of ASN networks updated in the database
        """

        # Prepare list by extracting AS values
        active_networks = list(
            map(int, map(lambda x: x.replace("AS", ""), active_networks))
        )
        updated_networks = 0
        
        # Running an atomic transaction.
        # Meaning that if something goes wrong in the process, all changes to the
        # database will be reverted to when the transaction started.
        #
        # This is to avoid having updated half of the networks in the databse and
        # thereafter crashing and being left with a half updated set of networks
        # connected to a hostingprovider. 
        logger.debug("Running atomic database transaction. Altered AS numbers:")
        with transaction.atomic():
            # Retrieve all ASN entries assosiated with this hosting provider
            hosting_provider = Hostingprovider.objects.get(pk=cls.hosting_provider_id)
            db_entries = GreencheckASN.objects.select_for_update().filter(
                hostingprovider=hosting_provider
            )

            # Iterate database entries
            for db_entry in db_entries:
                if db_entry.asn in active_networks:
                    active_networks.pop(active_networks.index(db_entry.asn))
                    db_entry.active = True
                    db_entry.save()

                    updated_networks += 1
                    logger.debug(db_entry)
                elif db_entry.active:
                    db_entry.active = False
                    db_entry.save()

                    updated_networks += 1
                    logger.debug(db_entry)

            # Iterate remaining list items (that are not in the database)
            if active_networks:
                for asn_network in active_networks:
                    db_entry, created = GreencheckASN.objects.update_or_create(
                        active=True, asn=asn_network, hostingprovider=hosting_provider
                    )
                    db_entry.save()

                    if created:
                        logger.debug(db_entry)

        return updated_networks

    def update_ip(cls, active_networks: List[str]) -> int:
        """
        General function that updates a hostingprovider's IPv4 and IPv6 networks.
        Under "networks" in this case, it is understood that it exists a IP and it's given subnet.
        Return: int, number of IP networks updated in the database
        """
        updated_networks = 0

        # Convert networks (xxx.xxx.xxx.xxx/yy) to a
        # start and end ip address
        tmp_list = []
        for ip_network in active_networks:
            network = ipaddress.ip_network(ip_network)
            tmp_list.append((str(network[1]), str(network[-1])))
        active_networks = list(set(tmp_list))

        # Running an atomic transaction.
        # Meaning that if something goes wrong in the process, all changes to the
        # database will be reverted to when the transaction started.
        #
        # This is to avoid having updated half of the networks in the databse and
        # thereafter crashing and being left with a half updated set of networks
        # connected to a hostingprovider. 
        logger.debug("Running atomic database transaction. Altered IP ranges:")
        with transaction.atomic():
            # Retrieve all IP(v4 and v6) entries assosiated to this hosting provider
            hosting_provider = Hostingprovider.objects.get(pk=cls.hosting_provider_id)
            db_entries = GreencheckIp.objects.select_for_update().filter(
                hostingprovider=hosting_provider
            )

            # Iterate database entries
            for db_entry in db_entries:
                if (db_entry.ip_start, db_entry.ip_end) in active_networks:
                    active_networks.pop(
                        active_networks.index((db_entry.ip_start, db_entry.ip_end))
                    )
                    db_entry.active = True
                    db_entry.save()

                    updated_networks += 1
                    logger.debug(db_entry)
                elif db_entry.active == True:
                    db_entry.active = False
                    db_entry.save()

                    updated_networks += 1
                    logger.debug(db_entry)

            # Iterate remaining list items (that are not in the database)
            if active_networks:
                for ip_network in active_networks:
                    db_entry, created = GreencheckIp.objects.update_or_create(
                        active=True,
                        ip_start=ip_network[0],
                        ip_end=ip_network[1],
                        hostingprovider=hosting_provider,
                    )
                    db_entry.save()

                    if created:
                        logger.debug(db_entry)

        return updated_networks
