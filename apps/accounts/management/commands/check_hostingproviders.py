import re
import time

from django.core.management.base import BaseCommand
import requests

from apps.accounts.models import Hostingprovider

URL = re.compile("^(https?:\/\/)?(.*)")
GREENCHECK_URL = "http://api.thegreenwebfoundation.org/greencheck/{}"


class Command(BaseCommand):
    help = "Check hostingprovider websites that they are green."

    def handle(self, *args, **options):
        all_hosters = Hostingprovider.objects.all()
        for host in all_hosters:
            match = URL.match(host.website)
            if match:
                url = match.group(2)
                resp = requests.get(GREENCHECK_URL.format(url)).json()
                time.sleep(1)
                if resp.get("green") is False:
                    host.showonwebsite = False
                    host.save()
