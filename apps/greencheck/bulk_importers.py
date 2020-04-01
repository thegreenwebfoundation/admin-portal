import csv
import ipaddress
import json
import logging
from io import StringIO

from apps.accounts.models import Hostingprovider
from apps.greencheck.models import GreencheckIp

logger = logging.getLogger(__name__)

class MissingHoster(Exception):
    pass


class MissingPath(Exception):
    pass


class ImporterCSV:
    def __init__(self, hoster: Hostingprovider, path):
        self.ips = []

        if not isinstance(hoster, Hostingprovider):
            raise MissingHoster("Expected a hosting provider")
        self.hoster = hoster

        if not path:
            raise MissingPath("Expected path to a CSV file")

        with open(path, "r+") as csvfile:
            rows = csv.reader(csvfile)
            self.fetch_ips(rows)

    def fetch_ips(self, rows):
        for row in rows:
            if row[0] == "IP":
                continue

            try:
                ip = ipaddress.IPv4Address(row[0])
                self.ips.append(ip)
            except ipaddress.AddressValueError:
                logger.exception(f"Couldn't load ipaddress for row: {row}")
            except Exception:
                logger.exception(f"New error, dropping to debug")
                import ipdb

                ipdb.set_trace()

    def run(self):

        green_ips = []
        for ip in self.ips:
            gcip, created = GreencheckIp.objects.update_or_create(
                active=True, ip_start=ip, ip_end=ip, hostingprovider=self.hoster
            )
            gcip.save()
            green_ips.append(gcip)

        return {"ipv4": green_ips}
