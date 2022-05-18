import abc
import requests

from apps.greencheck.management.commands.importers import importer_interface

from django.core.management.base import BaseCommand
from django.conf import settings


class EquinixImporter(metaclass=abc.ABCMeta):
    def fetch_data() -> list:
        try:
            response = requests.get(settings.EQUINIX_DATASET_ENDPOINT)

            list_of_ips = []
            for line in response.text.splitlines():
                # Filter out the lines with network information
                # (i.e. ip with subnet or AS numbers)
                if line.startswith("AS") or line[0].isdigit():
                    list_of_ips.append(
                        line.split(" ", 1)[0]
                    )  # Format as follows: IP range/ASN, Naming

            return list_of_ips
        except requests.RequestException:
            logger.warning("Unable to fetch and parse text file. Aborting early.")
            return
        except Exception:
            logger.exception("Something really unexpected happened. Aborting")


class Command(BaseCommand):
    def handle(self, *args, **options):
        EquinixImporter()  # Run importer

        # # Retrieve dataset and parse to networks
        # dataset = equinix.retrieve_dataset()

        # ip_ranges = equinix.extract_ip_ranges(dataset)
        # asns = equinix.update_asns_in_db(dataset)

        # green_ipv4s = [x for x in ip_ranges["ipv4"]]
        # green_ipv6s = [x for x in ip_ranges["ipv6"]]

        # self.stdout.write(
        #     f"Import Complete: Added {len(green_ipv4s)} new IPV4 networks, "
        #     f"{len(green_ipv6s) } IPV6 networks"
        # )
        # if asns:
        #     self.stdout.write(f"Added {len(asns)} AS Networks")
