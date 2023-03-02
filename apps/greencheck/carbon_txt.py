from apps.accounts.models.hosting import Hostingprovider
from typing import Dict, Set, List
import toml
import logging
import requests
from urllib import parse

from dateutil import relativedelta
import typing
import django
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

    def _create_green_domain_for_provider(self, domain: str, provider: Hostingprovider):
        """
        Create a Greendomain to match the newly created hosting provider
        """
        gc_models.GreenDomain.objects.create(
            url=domain,
            hosted_by=provider.name,
            hosted_by_id=provider.id,
            hosted_by_website=provider.website,
            partner=provider.partner,
            modified=timezone.now(),
            green=True,
        )
        # mark it as green using our label
        provider.staff_labels.add(ac_models.GREEN_VIA_CARBON_TXT)

    def _compare_evidence(
        self, found_provider: Hostingprovider, provider_dicts: typing.List[typing.Dict]
    ):
        """
        Check if the evidence in the provided provider_dict has already been
        added to the given provider. If not, return the evidence.


        """
        evidence = found_provider.supporting_documents.all()
        evidence_links = [item.url for item in evidence]
        new_evidence = []

        # this is checking the link, but not the type as well, as
        # not every piece of uploaded evidence has a type allocated
        for prov in provider_dicts:
            if prov["url"] not in evidence_links:
                new_evidence.append(prov)

        return new_evidence

    def _fetch_provider_from_dict(self, provider: dict) -> Dict:
        try:
            found_domain = gc_models.GreenDomain.objects.get(url=provider["domain"])
            return found_domain.hosting_provider
        except gc_models.GreenDomain.DoesNotExist:
            return None

    def _fetch_provider_from_domain_name(self, domain: str) -> Dict:
        try:
            found_domain = gc_models.GreenDomain.objects.get(url=domain)
            return found_domain.hosting_provider
        except gc_models.GreenDomain.DoesNotExist:
            return None

    def _fetch_provider(
        self,
        provider: typing.Union[typing.Dict, str],
        # domain: typing.Union[str, None] = None,
    ):
        """
        Accept either a string or a dict representing a provider, plus
        an optional domain, then try to find the corresponding provider
        in our database.
        """
        found_provider = None

        # we have our basic string version like "some-provider.com"
        if isinstance(provider, str):
            found_provider = self._fetch_provider_from_domain_name(provider)

        # we have our dict containing some sustainability credentials
        if isinstance(provider, dict):
            found_provider = self._fetch_provider_from_dict(provider)

        # Return the provider with all the extra evidence we can find
        return found_provider

    def parse(self, domain: str, carbon_txt: str) -> Dict:
        """
        Accept a domain and carbon_txt file, and return a data structure
        representing what information we have about the providers, related to
        their sustainability claims.
        For providers that we don't recognise, we
        """
        parsed_txt = toml.loads(carbon_txt)

        unregistered_evidence = []
        results = {"org": None, "upstream": [], "not_registered": {}}

        org = parsed_txt.get("org")
        if org:
            credentials = org.get("credentials")
            primary_creds = credentials[0]
            org_provider = self._fetch_provider(primary_creds)

            # filter for matching domains in case a carbon.txt is being used to
            # hold credentials for multiple similiar domains
            matching_domain_credentials = [
                cred
                for cred in credentials
                if cred["domain"] == primary_creds["domain"]
            ]
            # check for any new evidence for this domain
            new_org_evidence = self._compare_evidence(
                org_provider, matching_domain_credentials
            )

            # if the evidence
            if new_org_evidence:
                unregistered_evidence.extend(new_org_evidence)

            # either list as known provider, or add to the list
            # of new entities we do not have in our system yet
            if org_provider:
                results["org"] = org_provider
            else:
                results["not_registered"]["org"] = org

        # now do the same for upstream providers
        upstream = parsed_txt.get("upstream")
        if upstream:
            upstream_providers = upstream.get("providers")
            unregistered_providers = []

            for provider in upstream_providers:
                found_provider = self._fetch_provider(provider)
                if found_provider:
                    new_evidence = self._compare_evidence(found_provider, [provider])

                    if new_evidence:
                        unregistered_evidence.extend(new_evidence)

                    results["upstream"].append(found_provider)
                else:
                    unregistered_providers.append(provider)

            if unregistered_evidence:
                results["not_registered"]["evidence"] = unregistered_evidence

            results["not_registered"]["providers"] = unregistered_providers

        return results

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
        providers = []

        upstream = parsed_txt["upstream"]

        if upstream.get("providers"):
            providers = upstream["providers"]

        org_creds = parsed_txt["org"]["credentials"]

        # given a parsed carbon.txt object,
        # fetch the upstream providers
        for provider in providers:
            if provider:
                prov, upstream_providers = self._create_provider(
                    provider, upstream_providers
                )
                domain = provider["domain"]

                res = gc_models.GreenDomain.objects.filter(url=domain).first()
                if not res:
                    self._create_green_domain_for_provider(domain, prov)

                aliases = provider.get("aliases")
                if aliases:
                    for alias in aliases:
                        logger.info(f"Adding alias domain {alias} for {domain}")
                        self._create_green_domain_for_provider(alias, prov)

        # given a parsed carbon.txt object,  fetch the listed organisation
        org_domains = set()

        for org in org_creds:
            prov, org_providers = self._create_provider(org, org_providers)
            domain = org["domain"]

            res = gc_models.GreenDomain.objects.filter(url=domain).first()
            if not res:
                self._create_green_domain_for_provider(domain, prov)

            aliases = org.get("aliases")
            if aliases:
                for alias in aliases:
                    logger.info(f"Adding alias domain {alias} for {domain}")
                    self._create_green_domain_for_provider(alias, prov)

            org_domains.add(org["domain"])

        # we return the entities that we would query
        # for further information that should have been added
        # during parsing
        return {
            "upstream": {"providers": [*upstream_providers]},
            "org": {"providers": [*org_providers]},
        }

    def parse_and_preview(
        self, checked_domain: str = None, carbon_txt: str = None
    ) -> Dict:
        """
        Parses a carbon.txt string and returns a datastructure of the objects that
        the system was able to find, and what the new additions would look like.

        Used to show a preview for an administrator to approve
        before running an import.

        """
        parsed_txt = toml.loads(carbon_txt)
        result_data = {"upstream": {"providers": set()}, "org": None}

        upstream = parsed_txt["upstream"]
        providers = []

        if upstream.get("providers"):
            providers = upstream["providers"]

        # find our upstream
        for provider_representation in providers:
            if isinstance(provider_representation, str):
                # is it a domain string? if so, look for the matching provider
                try:
                    provider = gc_models.GreenDomain.objects.get(
                        url=provider_representation
                    ).hosting_provider
                    result_data["upstream"]["providers"].add(provider)
                except django.core.exceptions.ObjectDoesNotExist:
                    logger.warn(f"No provider found to match {provider_representation}")
                    pass

                # is it a dict-like object? If so,
                # find the matching provider for the domain property

            if isinstance(provider_representation, dict):
                # TODO one day we will use a better name than 'url'
                domain = provider_representation["domain"]

                try:
                    provider = gc_models.GreenDomain.objects.get(
                        url=domain
                    ).hosting_provider
                    result_data["upstream"]["providers"].add(provider)
                except django.core.exceptions.ObjectDoesNotExist:
                    logger.warn(f"No provider found to match {domain}")
                    pass

        # find our org. If information already exists, fetch it, so there's only one
        # canonical carbon.txt needed if there are multiple domains referring to the
        # same organisation
        try:
            provider = gc_models.GreenDomain.objects.get(
                url=checked_domain
            ).hosting_provider

            result_data["org"] = provider
            logger.info(provider)
        except django.core.exceptions.ObjectDoesNotExist:
            logger.warn(f"No provider found to match {checked_domain}")
            pass

        logger.info(result_data["org"])
        return result_data

    def import_from_url(self, url: str):
        """
        Try to fetch a carbon.txt file at a given url, and
        if successful, import the carbon.text file
        """
        res = requests.get(url)
        domain = parse.urlparse(url).netloc
        carbon_txt_string = res.content.decode("utf-8")

        return self.parse_and_import(domain, carbon_txt_string)
