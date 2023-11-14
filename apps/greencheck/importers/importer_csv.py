import logging
import pandas as pd

from typing import List
from apps.accounts.models.hosting import Hostingprovider

from apps.greencheck.importers.network_importer import (
    NetworkImporter,
    is_ip_network,
    is_ip_range,
    is_asn,
)
from apps.greencheck.importers.importer_interface import ImporterProtocol

from apps.greencheck.models import GreencheckIp, GreencheckASN
import ipaddress
from django.conf import settings

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

    def fetch_data_from_source(cls, filepath_or_buffer) -> List:
        """
        Return a list of the valid values from the provided CSV
        for importing
        """
        raw_data = pd.read_csv(filepath_or_buffer, header=None)

        return cls.parse_to_list(raw_data)

    def parse_to_list(self, raw_data: pd.DataFrame) -> List:
        """
        Parse the provided pandas DataFrame, and return a flattened list
        of ip ranges, or importable IP networks, or AS numbers
        """
        rows = raw_data.values
        imported_networks = {"asns": [], "ip_networks": [], "ip_ranges": []}
        for row in rows:
            # try read the IP Network
            if is_ip_network(row[0]):
                logger.info(f"IP Network found. Adding {row[0]}")
                imported_networks["ip_networks"].append(row[0])
                continue

            # try for an ASN
            if is_asn(row[0]):
                imported_networks["asns"].append(row[0])
                continue

            # finally, try to parse out an IP Range
            first_ip = row[0].strip()
            null_second_column = pd.isnull(row[1])
            last_ip = None if null_second_column else row[1].strip()
            ip_range_found = is_ip_range((first_ip, last_ip))

            if ip_range_found:
                imported_networks["ip_ranges"].append((first_ip, last_ip))
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
