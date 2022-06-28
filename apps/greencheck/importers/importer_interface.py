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
            # Prepare ASN and IP lists
            regex = re.compile("(AS)[0-9]+$")
            asn_list = list(filter(regex.match, list_of_addresses))
            ip_list = list(set(list_of_addresses) - set(asn_list))

            # Final ASN preparation and run updater
            asn_list = list(map(lambda x: x.replace("AS", ""), asn_list))
            count_asn = cls.update_asn(cls, asn_list)

            # Final IP preparation and run updater
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

            return f"Processing complete. Updated {count_asn} ASN's and {count_ip} IP's (either IPv4 and/or IPv6)"
        except ValueError:
            logger.exception(
                "Value has invalid structure. Must be IPv4 or IPv6 with subnetmask (101.102.103.104/27) or AS number (AS123456)."
            )
            return f"An error occurred while adding new entries. Updated {count_asn} ASN's and {count_ip} IP's (either IPv4 and/or IPv6)"
        except Exception as e:
            logger.exception("Something really unexpected happened. Aborting")
            logger.exception(e)
            return f"An error occurred while adding new entries. Updated {count_asn} ASN's and {count_ip} IP's (either IPv4 and/or IPv6)"

    def update_asn(cls, active_addresses: List[str]):
        updated_addresses = 0
        hosting_provider = Hostingprovider.objects.get(pk=cls.hosting_provider_id)

        # Retrieve all ASN entries assosiated to this hosting provider
        entries = GreencheckASN.objects.select_for_update().filter(
            hostingprovider=hosting_provider
        )

        logger.debug("Running atomic database transaction. Altered AS numbers:")
        with transaction.atomic():
            # Iterate database entries
            for entry in entries:
                if entry.asn in active_addresses:
                    entry.active = True
                    entry.save()

                    updated_addresses += 1
                    logger.debug(entry)
                elif entry.active == True:
                    entry.active = False
                    entry.save()

                    updated_addresses += 1
                    logger.debug(entry)

            # # Iterate remaining list items (that are not in the database)
            # if active_addresses:
            #     for address in active_addresses:
            #         # # TODO: FOLLOWING NEEDS SOME WORK. 
            #         # OPTION 1
            #         entry, created = GreencheckASN.objects.update_or_create(
            #             active=True, asn=address, hostingprovider=hosting_provider
            #         )
            #         entry.save()

            #         if created:
            #             logger.debug(entry)

            #         # OPTION 2
            #         entry = GreencheckASN.objects.filter(hostingprovider=hosting_provider, asn=address).first()
            #         if entry == False:
            #             entry.active = True
            #             entry.save()

            #             updated_addresses += 1
            #             logger.debug(entry)

        return updated_addresses

    def update_ip(cls, active_addresses: List[str]):
        updated_addresses = 0

        # Convert list of networks (ip with subnet) to list of
        # start and end ip addresses.
        tmp_list = []
        for address in active_addresses:
            network = ipaddress.ip_network(address)
            tmp_list.append((str(network[1]), str(network[-1])))
        active_addresses = tmp_list

        # Retrieve all IP(v4 and v6) entries assosiated to this hosting provider
        hosting_provider = Hostingprovider.objects.get(pk=cls.hosting_provider_id)
        entries = GreencheckIp.objects.select_for_update().filter(
            hostingprovider=hosting_provider
        )

        logger.debug("Running atomic database transaction. Altered IP ranges:")
        with transaction.atomic():
            # Iterate database entries
            for entry in entries:
                if (entry.ip_start, entry.ip_end) in active_addresses:
                    active_addresses.pop(
                        active_addresses.index((entry.ip_start, entry.ip_end))
                    )
                    entry.active = True
                    entry.save()

                    updated_addresses += 1
                    logger.debug(entry)
                elif entry.active == True:
                    entry.active = False
                    entry.save()

                    updated_addresses += 1
                    logger.debug(entry)

            # Iterate remaining list items (that are not in the database)
            # if active_addresses:
            #     for address in active_addresses:
                    # # TODO: FOLLOWING NEEDS SOME WORK. 
                    # # OPTION 1
                    # entry, created = GreencheckIp.objects.update_or_create(
                    #     active=True,
                    #     ip_start=address[0],
                    #     ip_end=address[1],
                    #     hostingprovider=hosting_provider,
                    # )
                    # entry.save()

                    # if created:
                    #     logger.debug(entry)

                    # # OPTION 2
                    # entry = GreencheckIp.objects.filter(hostingprovider=hosting_provider, 
                    #     ip_start=address[0],
                    #     ip_end=address[1]).first()
                        
                    # pdb.set_trace()
                    # if entry.active == False:
                    #     entry.active = True
                    #     entry.save()

                    #     updated_addresses += 1
                    #     logger.debug(entry)

        return updated_addresses
