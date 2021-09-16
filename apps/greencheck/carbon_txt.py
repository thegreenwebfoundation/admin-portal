from typing import Dict
import toml
import rich
import logging

from dateutil import relativedelta


from django.utils import timezone
from ..accounts import models as ac_models

logger = logging.getLogger(__name__)


class CarbonTxtParser:
    """
    A parser for reading carbon.txt files and turning them into domain objects
    we can use for updating information about provider organisations in
    the green web database.
    """

    def parse_and_import(self, domain: str = None, carbon_txt: str = None) -> Dict:
        """
        Accept a domain representing where the carbon.txt file
        comes form, and a string containing the carbon.txt
        contents, and import the organisations listed, returning
        the providers
        """
        # what we need

        # parse a carbon.txt file, plus where it is fetched from
        # (request, DNS lookup) and return a set of providers and
        # pieces of supporting evidence
        parsed_txt = toml.loads(carbon_txt)
        upstream_providers = set()
        org_providers = set()

        providers = parsed_txt["upstream"]["providers"]
        org_creds = parsed_txt["org"]["credentials"]

        # given a parsed carbon.txt object,
        # fetch the upstream providers
        for provider in providers:
            prov, created = ac_models.Hostingprovider.objects.get_or_create(
                website=provider["domain"]
            )
            if not prov.name:
                prov.name = provider["domain"]
            if prov not in upstream_providers:
                upstream_providers.add(prov)
            SupportingDoc = ac_models.HostingProviderSupportingDocument

            found_docs = SupportingDoc.objects.filter(
                hostingprovider=prov, url=provider["url"]
            )
            doc = None

            if found_docs:
                doc = found_docs[0]

            if not found_docs:
                title = f"{provider['domain']} - {provider['doctype']}"
                doc = SupportingDoc.objects.create(
                    url=provider["url"],
                    hostingprovider=prov,
                    title=title,
                    valid_from=timezone.now(),
                    valid_to=timezone.now() + relativedelta.relativedelta(years=1),
                )
                logger.info(f"New supporting doc {doc} for {prov}")

        # given a parsed carbon.txt object,  fetch the listed organisation
        org_domains = set()

        for org in org_creds:
            if org["domain"] not in org_domains:
                prov, created = ac_models.Hostingprovider.objects.get_or_create(
                    website=org["domain"]
                )
                if not prov.name:
                    prov.name = org["domain"]
                org_providers.add(prov)

                found_docs = SupportingDoc.objects.filter(
                    hostingprovider=prov, url=provider["url"]
                )
                doc = None

                if found_docs:
                    doc = found_docs[0]

                if not found_docs:
                    title = f"{org['domain']} - {org['doctype']}"
                    doc = SupportingDoc.objects.create(
                        url=org["url"],
                        hostingprovider=prov,
                        title=title,
                        valid_from=timezone.now(),
                        valid_to=timezone.now() + relativedelta.relativedelta(years=1),
                    )
                    logger.info(f"New supporting doc {doc} for {prov}")

            org_domains.add(org["domain"])

        # we return the entities that we would query
        # for further information that should have been added
        # during parsing
        return {
            "upstream": {"providers": [*upstream_providers]},
            "org": {"providers": [*org_providers]},
        }
