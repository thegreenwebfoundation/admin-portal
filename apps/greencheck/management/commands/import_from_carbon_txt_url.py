import logging
from django.core.management.base import BaseCommand

from ... import models as gc_models
from ... import carbon_txt

logger = logging.getLogger(__name__)
# console = logging.StreamHandler()
# logger.addHandler(console)
# logger.setLevel(logging.DEBUG)


class Command(BaseCommand):

    help = (
        "Fetch a carbon.txt file from the URL provided and import the providers "
        "with any supporting evidence associated."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "url",
            type=str,
            help="The fully qualified URL to download the carbon.txt file from",
        )

    def handle(self, *args, **options):
        """
        """
        import_url = options["url"]
        parser = carbon_txt.CarbonTxtParser()
        res = parser.import_from_url(import_url)
        self.stdout.write(f"OK. Import successful. Imported the following providers:")

        flattened_provider_list = [
            *res["upstream"]["providers"],
            *res["org"]["providers"],
        ]

        for provider in flattened_provider_list:
            self.stdout.write(f"Imported {provider}")

