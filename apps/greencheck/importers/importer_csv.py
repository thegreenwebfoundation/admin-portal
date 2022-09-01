import requests
import logging
import pandas as pd
import ipdb
import re
import ipaddress
import rich
from typing import List
from apps.accounts.models.hosting import Hostingprovider

from apps.greencheck.importers.importer_interface import BaseImporter, Importer
from apps.greencheck.models import GreencheckIp, GreencheckASN

from django.conf import settings

logger = logging.getLogger(__name__)


class CSVImporter(BaseImporter):
    def __init__(self, provider: Hostingprovider):
        self.hosting_provider = provider

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

            # just one column? it's probably an AS or a IP network
            if pd.isnull(row[1]):

                # is it an AS number?
                if row[0].startswith("AS"):
                    # split out the as number from the row,
                    # add check for people getting AS number
                    as_number = row[0].split("AS ")[0]
                    just_as_with_no_number = as_number.lower() == "as"

                    if as_number and not just_as_with_no_number:
                        imported_networks["asns"].append(row[0])
                else:
                    # if it isn't an AS number it's probably an IP network
                    try:
                        ip_network = ipaddress.ip_network(row[0])
                        imported_networks["ip_networks"].append(row[0])
                    except Exception:
                        logger.warn(
                            f"Item {row[0]} was not an ip network. Not importing."
                        )
            else:
                try:
                    first_ip, last_ip = row[0].strip(), row[1].strip()
                    ip_begin = ipaddress.ip_address(first_ip)
                    ip_end = ipaddress.ip_address(last_ip)
                    imported_networks["ip_ranges"].append((first_ip, last_ip))
                except Exception:
                    logger.warn(
                        f"Row {row} does not look like an IP address. Not importing"
                    )

        flattened_network_list = [
            *imported_networks["asns"],
            *imported_networks["ip_networks"],
            *imported_networks["ip_ranges"],
        ]

        return flattened_network_list

    def preview(self, provider: Hostingprovider, list_of_networks: List) -> List:
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

            if self.is_as_number(network):
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

            if ip_network := self.is_ip_network(network):
                try:
                    green_ip = GreencheckIp.objects.get(
                        active=True,
                        ip_start=ip_network[1],
                        ip_end=ip_network[-1],
                        hostingprovider=provider,
                    )
                    green_ips.append(green_ip)

                except GreencheckIp.DoesNotExist:
                    green_ip = GreencheckIp(
                        active=True,
                        ip_start=ip_network[1],
                        ip_end=ip_network[-1],
                        hostingprovider=provider,
                    )
                    green_ips.append(green_ip)

            if ip_range := self.is_ip_range(network):
                try:
                    green_ip = GreencheckIp.objects.get(
                        active=True,
                        hostingprovider=provider,
                        ip_start=ip_range[0],
                        ip_end=ip_range[1],
                    )
                    green_ips.append(green_ip)
                except GreencheckIp.DoesNotExist:
                    green_ip = GreencheckIp(
                        active=True,
                        hostingprovider=provider,
                        ip_start=ip_range[0],
                        ip_end=ip_range[1],
                    )
                    green_ips.append(green_ip)

        # or make a new one, in memory
        return {"green_ips": green_ips, "green_asns": green_asns}
