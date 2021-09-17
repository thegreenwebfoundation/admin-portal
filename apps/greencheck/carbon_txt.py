from apps.accounts.models.hosting import Hostingprovider
from typing import Dict, Set, List
import toml
import rich
import logging
import requests
from urllib import parse

from dateutil import relativedelta


from django.utils import timezone
from ..accounts import models as ac_models
from . import models as gc_models

logger = logging.getLogger(__name__)


class CarbonTxtParser:
    """
    A parser for reading carbon.txt files and turning them into domain objects
    we can use for updating information about provider organisations in
    the green web database.
    """

    def _create_provider(self, provider_dict: dict, provider_set: Set) -> List:
        """
        Create a hosting provider from the provider dict passed
        in, and return a dict of the created hosting provider, and
        updated provider set.

        The provider matching the domain already exists, add the supporting evidence
        without creating a new provider.
        """
        prov, created = ac_models.Hostingprovider.objects.get_or_create(
            website=provider_dict["domain"]
        )
        if not prov.name:
            prov.name = provider_dict["domain"]
            prov.save()
        if prov not in provider_set:
            provider_set.add(prov)
        SupportingDoc = ac_models.HostingProviderSupportingDocument

        found_docs = SupportingDoc.objects.filter(
            hostingprovider=prov, url=provider_dict["url"]
        )
        doc = None

        if found_docs:
            doc = found_docs[0]

        if not found_docs:
            title = f"{provider_dict['domain']} - {provider_dict['doctype']}"
            doc = SupportingDoc.objects.create(
                url=provider_dict["url"],
                hostingprovider=prov,
                title=title,
                valid_from=timezone.now(),
                valid_to=timezone.now() + relativedelta.relativedelta(years=1),
            )
            logger.info(f"New supporting doc {doc} for {prov}")

        # rich.inspect({"provider": prov, "provider_set": provider_set})

        return [prov, provider_set]

    def _create_green_domain_for_provider(
        self, provider_dict: dict, provider: Hostingprovider
    ):
        """
        Create a Greendomain to match the newly created hosting provider
        """
        gc_models.GreenDomain.objects.create(
            url=provider_dict["domain"],
            hosted_by=provider.name,
            hosted_by_id=provider.id,
            hosted_by_website=provider.website,
            partner=provider.partner,
            modified=timezone.now(),
            green=True,
        )

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

            prov, upstream_providers = self._create_provider(
                provider, upstream_providers
            )

            res = gc_models.GreenDomain.objects.filter(url=provider["domain"]).first()
            if not res:
                self._create_green_domain_for_provider(provider, prov)

        # given a parsed carbon.txt object,  fetch the listed organisation
        org_domains = set()

        for org in org_creds:
            prov, org_providers = self._create_provider(org, org_providers)

            res = gc_models.GreenDomain.objects.filter(url=org["domain"]).first()
            if not res:
                self._create_green_domain_for_provider(org, prov)

            org_domains.add(org["domain"])

        # we return the entities that we would query
        # for further information that should have been added
        # during parsing
        return {
            "upstream": {"providers": [*upstream_providers]},
            "org": {"providers": [*org_providers]},
        }

    def parse_and_preview(self, url: str, carbon_txt: str = None) -> Dict:
        """
        Parses a carbon.txt string and returns a preview of the objects that would be created if it was imported.

        Used to show a preview for an administrator to approve
        before running an import.

        """
        # not implemented
        pass

    def import_from_url(self, url: str):
        """
        Try to fetch a carbon.txt file at a given url, and
        if successful, import the carbon.text file
        """
        res = requests.get(url)
        domain = parse.urlparse(url).netloc
        carbon_txt_string = res.content.decode("utf-8")

        return self.parse_and_import(domain, carbon_txt_string)

