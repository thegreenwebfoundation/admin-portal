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

    def process_addresses(cls, list_of_updatable_networks: list):
        """
        General function that processes all types of addresses (IPv4, IPv6 and ASN).

        The list that is given to this function is considered a list of active networks
        and the process that is taking place is changing the state of these addresses
        in the database in terms of their state.

        Addresses in the list will be set as active, and other addresses in the database
        will be set to inactive.
        Return: str, success message containing the number of updated networks
        """
        # Set temporary counters
        count_ip = 0
        count_asn = 0

        try:
            # Prepare: Extract ASN networks
            regex = re.compile("(AS)[0-9]+$")
            asn_list = list(set(filter(regex.match, list_of_updatable_networks)))

            # Run ASN update
            count_asn = cls.update_asn(cls, asn_list)

            # Prepare: Extract IP networks
            ip_list = list(set(list_of_updatable_networks) - set(asn_list))

            # Prepare: Type checking
            ip_list = list(
                filter(
                    lambda x: isinstance(
                        ipaddress.ip_network(x),
                        (ipaddress.IPv4Network, ipaddress.IPv6Network),
                    ),
                    ip_list,
                )
            )

            # Run IP update
            count_ip = cls.update_ip(cls, ip_list)

            # Success
            return """Import complete. Updated {asn} ASN and {ip} IP networks 
            (v4 and/or v6)""".format(
                asn=count_asn, ip=count_ip
            )
        except ValueError:
            logger.exception(
                """Value has invalid structure. Must be IPv4 or IPv6 with subnetmask 
                (x.x.x.x/yy) or AS number (AS123456)."""
            )

            return """Import aborted as an error occured. Updated {asn} ASN and {ip} IP networks 
            (v4 and/or v6)""".format(
                asn=count_asn, ip=count_ip
            )
        except Exception as e:
            logger.exception(
                "Import aborted. Something unexpected happened."
            )
            logger.exception(e)
            
            return """Import aborted as an error occured. Updated {asn} ASN and {ip} IP networks 
            (v4 and/or v6)""".format(
                asn=count_asn, ip=count_ip
            )

    def update_asn(cls, active_asn_networks: List[str]) -> int:
        """
        General function that updates a hostingprovider's ASN networks.
        Under "networks" in this case, it is understood that it needs to have a format
        similar to for example: AS12345.

        Return: int, number of ASN networks updated in the database
        """
        # Prepare list by extracting the "AS" prefix
        active_asn_networks = list(
            map(int, map(lambda x: x.replace("AS", ""), active_asn_networks))
        )

        # Set temporary counter
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
            # from the database
            hosting_provider = Hostingprovider.objects.get(pk=cls.hosting_provider_id)
            db_entries = GreencheckASN.objects.select_for_update().filter(
                hostingprovider=hosting_provider
            )

            # Iterate through database entries
            # Sets:
            # A = database entries
            # B = given list of active networks
            for db_entry in db_entries:
                if db_entry.asn in active_asn_networks:
                    # Update: A ∩ B
                    # Meaning: Database entry is found in active list

                    # Remove database entry from list of active ASN networks
                    active_asn_networks.pop(active_asn_networks.index(db_entry.asn))

                    # Make sure to set the database entry to active and save it
                    db_entry.active = True
                    db_entry.save()

                    # Update counter and log
                    updated_networks += 1
                    logger.debug(db_entry)
                elif db_entry.active:
                    # Update: A
                    # Meaning: Only present in datbase with an active status, but not
                    # in the list of active networks so it must be set to inactive
                    db_entry.active = False
                    db_entry.save()

                    # Update counter and log
                    updated_networks += 1
                    logger.debug(db_entry)

            # Update: B
            # Meaning: Only present in list of active networks, but not in database.
            # So this must be a new network that needs to be added to the databse.
            if active_asn_networks:
                # Only execute if the list still has some remaining items.

                for asn_network in active_asn_networks:
                    # Create new entry in the database
                    db_entry, created = GreencheckASN.objects.update_or_create(
                        active=True, asn=asn_network, hostingprovider=hosting_provider
                    )
                    db_entry.save()

                    # Update counter and log if creation was successful
                    if created:
                        updated_networks += 1
                        logger.debug(db_entry)

        return updated_networks

    def update_ip(cls, active_ip_networks: List[str]) -> int:
        """
        General function that updates a hostingprovider's IPv4 and IPv6 networks.
        Under "networks" in this case, it is understood that it exists a IP and its
        given subnet.

        Return: int, number of IP networks updated in the database
        """
        # Prepare list by extracting the beginning and ending address of a given
        # IP network.
        # This is needed since the database only saves a beginning and ending address
        # and not a IP with a subnet.
        tmp_list = []
        for ip_network in active_ip_networks:
            network = ipaddress.ip_network(ip_network)
            tmp_list.append((str(network[1]), str(network[-1])))
        active_ip_networks = list(set(tmp_list))

        # Set temporary counter
        updated_networks = 0

        # Running an atomic transaction.
        # Meaning that if something goes wrong in the process, all changes to the
        # database will be reverted to when the transaction started.
        #
        # This is to avoid having updated half of the networks in the databse and
        # thereafter crashing and being left with a half updated set of networks
        # connected to a hostingprovider.
        logger.debug("Running atomic database transaction. Altered IP ranges:")
        with transaction.atomic():
            # Retrieve all IP entries assosiated with this hosting provider
            # from the database
            hosting_provider = Hostingprovider.objects.get(pk=cls.hosting_provider_id)
            db_entries = GreencheckIp.objects.select_for_update().filter(
                hostingprovider=hosting_provider
            )

            # Iterate through database entries
            # Sets:
            # A = database entries
            # B = given list of active networks
            for db_entry in db_entries:
                if (db_entry.ip_start, db_entry.ip_end) in active_ip_networks:
                    # Update: A ∩ B
                    # Meaning: Database entry is found in active list

                    # Remove database entry from list of active IP networks
                    active_ip_networks.pop(
                        active_ip_networks.index((db_entry.ip_start, db_entry.ip_end))
                    )

                    # Make sure to set the database entry to active and save it
                    db_entry.active = True
                    db_entry.save()

                    # Update counter and log
                    updated_networks += 1
                    logger.debug(db_entry)
                elif db_entry.active:
                    # Update: A
                    # Meaning: Only present in datbase with an active status, but not
                    # in the list of active networks so it must be set to inactive
                    db_entry.active = False
                    db_entry.save()

                    # Update counter and log
                    updated_networks += 1
                    logger.debug(db_entry)

            # Update: B
            # Meaning: Only present in list of active networks, but not in database.
            # So this must be a new network that needs to be added to the databse.
            if active_ip_networks:
                # Only execute if the list still has some remaining items.

                for ip_network in active_ip_networks:
                    # Create new entry in the database
                    db_entry, created = GreencheckIp.objects.update_or_create(
                        active=True,
                        ip_start=ip_network[0],
                        ip_end=ip_network[1],
                        hostingprovider=hosting_provider,
                    )
                    db_entry.save()

                    # Update counter and log if creation was successful
                    if created:
                        logger.debug(db_entry)

        return updated_networks
