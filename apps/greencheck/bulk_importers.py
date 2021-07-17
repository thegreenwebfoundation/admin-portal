import csv
import ipaddress
import logging

from apps.accounts.models import Hostingprovider
from apps.greencheck.models import GreencheckIp

logger = logging.getLogger(__name__)


class MissingHoster(Exception):
    pass


class MissingPath(Exception):
    pass


class ImporterCSV:
    def __init__(self, hoster: Hostingprovider):
        self.ips = []

        if not isinstance(hoster, Hostingprovider):
            raise MissingHoster("Expected a hosting provider")
        self.hoster = hoster

    def ips_from_path(self, path):
        """
        Accept a path to a file, and read it, adding IP
        ranges in the file to the local ips array
        """

        if not path:
            raise MissingPath("Expected path to a CSV file")

        with open(path, "r+") as csvfile:
            rows = csv.reader(csvfile)
            self.fetch_ips(rows)

    def ips_from_file(self, fileObj):
        rows = csv.reader(fileObj)
        self.fetch_ips(rows)

    def fetch_ips(self, rows):
        for row in rows:
            if "IP" in row[0].upper():
                continue

            try:
                ip = ipaddress.IPv4Address(row[0])
                self.ips.append(ip)
            except ipaddress.AddressValueError:
                logger.exception(f"Couldn't load ipaddress for row: {row}")
            except Exception:
                logger.exception("New error, dropping to debug")
                import ipdb

                ipdb.set_trace()

    def preview(self, provider):
        """
        Return a list of the GreencheckIPs that would be updated
        or created based on the current provided file.
        """

        green_ip_list = []
        # try to find a GreenIP
        for ip in self.ips:
            try:
                green_ip = GreencheckIp.objects.get(
                    ip_start=ip, ip_end=ip, active=True, hostingprovider=provider
                )
                green_ip_list.append(green_ip)
            except GreencheckIp.DoesNotExist:
                green_ip = GreencheckIp(
                    active=True, ip_start=ip, ip_end=ip, hostingprovider=provider
                )
                green_ip_list.append(green_ip)

        # or make a new one, in memory
        return green_ip_list

    def run(self):

        created_ips = []
        updated_ips = []
        for ip in self.ips:
            gcip, created = GreencheckIp.objects.update_or_create(
                active=True, ip_start=ip, ip_end=ip, hostingprovider=self.hoster
            )
            gcip.save()
            if created:
                created_ips.append(gcip)
            if gcip and not created:
                updated_ips.append(gcip)

        return {"ipv4": {"created": created_ips, "updated": updated_ips}}
