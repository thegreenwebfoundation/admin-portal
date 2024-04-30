import csv
import ipaddress
import logging
from typing import List, Tuple, Union

from apps.accounts.models.hosting import Hostingprovider
from apps.greencheck.importers.importer_interface import ImporterProtocol
from apps.greencheck.importers.network_importer import (
    NetworkImporter,
    is_asn,
    is_ip_network,
    is_ip_range,
    ip_address_without_subnet_mask,
)
from apps.greencheck.models import GreencheckASN, GreencheckIp

logger = logging.getLogger(__name__)


class NoProviderException(Exception):
    pass


class CSVImporter:
    def __init__(self):
        self.processed_ips = []

    def process(self, provider: Hostingprovider = None, list_of_networks: list = None):
        if not provider:
            raise NoProviderException

        network_importer = NetworkImporter(provider)
        network_importer.deactivate_ips()
        return network_importer.process_addresses(list_of_networks)

    def fetch_data_from_source(cls, file_like_object) -> List[List]:
        """
        Return a list of the valid values from the provided CSV
        for importing
        """
        row_list = []
        csvfile = csv.reader(file_like_object)
        for row in csvfile:
            row_list.append(row)

        return row_list

    def parse_to_list(self, raw_data) -> List[Union[str, Tuple]]:
        """
        Accept a list of values, and return a flattened list
        of ip ranges, or importable IP networks, or AS numbers
        """

        # breakpoint()
        imported_networks = {"asns": [], "ip_networks": [], "ip_ranges": []}

        for row in raw_data:

            # skip empty rows
            if not row:
                continue

            logger.debug(f"Processing row: {row}")
            # try read the IP Network
            if is_ip_network(row[0].strip()):
                logger.info(f"IP Network found. Adding {row[0]}")
                imported_networks["ip_networks"].append(row[0])
                continue

            # try for an ASN
            if is_asn(row[0]):
                logger.info(f"ASN found. Adding {row[0]}")
                imported_networks["asns"].append(row[0])
                continue

            # finally, try to parse out an IP Range
            first_ip = row[0].strip()
            if len(row) > 1:
                second_ip = row[1].strip()
            else:
                second_ip = None

            # for a sole IP address on a row, set the second_ip to the same
            # as the first ip, so we can treat it as a range of length 1.
            if not second_ip:
                second_ip = first_ip

            if "/" in first_ip:
                first_ip = ip_address_without_subnet_mask(first_ip)

            if "/" in second_ip:
                second_ip = ip_address_without_subnet_mask(second_ip)

            ip_range_found = is_ip_range((first_ip, second_ip))

            if ip_range_found:
                logger.info(f"IP Range found. Adding {row[0]}")
                imported_networks["ip_ranges"].append((first_ip, second_ip))
                continue

            logger.warn(
                f"No valid networks or IP ranges identified in row {row}  Not importing"
            )

        flattened_network_list = [
            *imported_networks["asns"],
            *imported_networks["ip_networks"],
            *imported_networks["ip_ranges"],
        ]

        return flattened_network_list

    def preview(
        self, provider: Hostingprovider = None, list_of_networks: List = None
    ) -> List:
        """
        Return a list of the GreencheckIPs that would be updated
        or created based on the current provided file.

        Return a preview of the networks to import, suitable for displaying
        in a webpage.
        """

        green_ips = []
        green_asns = []
        # try to find a GreenIP
        for network in list_of_networks:
            if is_asn(network):
                # this looks like an AS number
                try:
                    as_number = network.split("AS")[1]
                    green_asn = GreencheckASN.objects.get(
                        asn=as_number, active=True, hostingprovider=provider
                    )
                    green_asns.append(green_asn)
                except GreencheckASN.DoesNotExist:
                    green_asn = GreencheckASN(
                        active=True, asn=as_number, hostingprovider=provider
                    )
                    green_asns.append(green_asn)
                continue

            if is_ip_network(network):
                # create an ip network from the
                # network address/network prefix
                # pair
                ip_network = ipaddress.ip_network(network)
                try:
                    green_ip = GreencheckIp.objects.get(
                        active=True,
                        ip_start=ip_network[0],
                        ip_end=ip_network[-1],
                        hostingprovider=provider,
                    )
                    green_ips.append(green_ip)

                except GreencheckIp.DoesNotExist:
                    green_ip = GreencheckIp(
                        active=True,
                        ip_start=ip_network[0],
                        ip_end=ip_network[-1],
                        hostingprovider=provider,
                    )
                    green_ips.append(green_ip)
                continue

            if is_ip_range(network):
                try:
                    green_ip = GreencheckIp.objects.get(
                        active=True,
                        hostingprovider=provider,
                        ip_start=network[0],
                        ip_end=network[1],
                    )
                    green_ips.append(green_ip)
                except GreencheckIp.DoesNotExist:
                    green_ip = GreencheckIp(
                        active=True,
                        hostingprovider=provider,
                        ip_start=network[0],
                        ip_end=network[1],
                    )
                    green_ips.append(green_ip)
                continue

        # or make a new one, in memory
        return {"green_ips": green_ips, "green_asns": green_asns}


assert isinstance(CSVImporter(), ImporterProtocol)
