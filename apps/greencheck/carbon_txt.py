import logging
import typing
from typing import Dict, List, Set, Union
from urllib import parse
import hashlib
import dns.resolver
import requests
import toml
from dateutil import relativedelta
from django.utils import timezone

from apps.accounts.models.hosting import Hostingprovider

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

        # check if this is provider string, not a dict we can inspect
        # if so, return early
        for prov in provider_dicts:
            if isinstance(prov, str):
                return []

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

    def _check_domain_hash_against_provider(self, hash: str, domain: str) -> bool:
        """
        Accept a SHA256 hash, a domain name, and check that
        making a hash with the domain and shared secret for the provider
        linked to that domain produces the same value as the provided hash.
        Returns a true boolean result, if there is a match
        """

        try:
            provider = gc_models.GreenDomain.objects.get(url=domain).hosting_provider
        except Exception as ex:
            logger.exception(
                f"There was an error finding a provider for domain: {domain} - {ex}"
            )
            return False

        res = hashlib.sha256(f"{domain} {provider.shared_secret}".encode("utf-8"))

        return res.hexdigest() == hash

    def _fetch_provider(
        self,
        provider: typing.Union[typing.Dict, str],
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
            if org_provider:
                new_org_evidence = self._compare_evidence(
                    org_provider, matching_domain_credentials
                )

                # if there is evidence, add it to the list
                if new_org_evidence:
                    unregistered_evidence.extend(new_org_evidence)

                results["org"] = org_provider
            # either list as known provider, or add to the list
            # of new entities we do not have in our system yet

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

    def _check_for_carbon_txt_dns_record(self, domain: str) -> Union[str, None]:
        try:
            answers = dns.resolver.resolve(domain, "TXT")
        except dns.resolver.NoAnswer:
            return None

        carb_txt_record = []
        domain_hash_match = None

        for answer in answers:
            txt_record = answer.to_text().strip('"')
            if txt_record.startswith("carbon-txt"):
                # pull our url
                _, txt_record_body = txt_record.split("=")

                domain_hash_check = txt_record_body.split(" ")

                if len(domain_hash_check) == 1:
                    override_url = domain_hash_check[0]
                    carb_txt_record.append(override_url)

                if len(domain_hash_check) == 2:
                    override_url = domain_hash_check[0]
                    domain_hash = domain_hash_check[1]

                    carb_txt_record.append(override_url)
                    override_domain = parse.urlparse(override_url).netloc
                    matched_domain_hash = self._check_domain_hash_against_provider(
                        domain_hash, override_domain
                    )

                    if matched_domain_hash:
                        # create our new domain
                        provider = gc_models.GreenDomain.objects.get(
                            url=override_domain
                        ).hosting_provider

                        gc_models.GreenDomain.create_for_provider(domain, provider)

                carb_txt_record.append(override_url)

        if carb_txt_record:
            return carb_txt_record[0], False

    def parse_from_url(self, url: str):
        """
        Try to fetch a carbon.txt file at a given url, and
        if successful, returned the parsed view after carrying
        out lookups
        """

        # look in the headers for a "via" header, and if present, use that
        # Via: 1.1 intermediate.domain.com
        # if there is a valid domain where we have a match, add it to our upstream list

        parsed = parse.urlparse(url)
        url_domain = parsed.netloc

        lookup_sequence = []
        lookup_sequence.append(url)

        # do DNS lookup. to see if we have an override url to use instead
        override_url, matched_dns_hash = self._check_for_carbon_txt_dns_record(
            url_domain
        )

        if override_url:
            res = requests.get(override_url)
            lookup_sequence.append(override_url)
            url_domain = parse.urlparse(override_url).netloc

        else:
            res = requests.get(url)

        if "via" in res.headers.keys():
            protocol, via_url, *domain_hash = res.headers["via"].split(" ")
            lookup_sequence.append(via_url)
            res = requests.get(via_url)

            url_domain = parse.urlparse(via_url).netloc

            if domain_hash:
                try:
                    matched_domain_hash = self._check_domain_hash_against_provider(
                        domain_hash[0], url_domain
                    )

                    if matched_domain_hash:
                        # create our new domain
                        provider = gc_models.GreenDomain.objects.get(
                            url=url_domain
                        ).hosting_provider

                        gc_models.GreenDomain.create_for_provider(
                            parsed.netloc, provider
                        )
                except Exception as ex:
                    logger.exception(
                        f"Unable to create the green domain for: {parsed.netloc} - {ex}"
                    )

        carbon_txt_string = res.content.decode("utf-8")

        parsed_carbon_txt = self.parse(url_domain, carbon_txt_string)

        parsed_carbon_txt["lookup_sequence"] = lookup_sequence

        return parsed_carbon_txt

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

    def import_from_url(self, url: str):
        """
        Try to fetch a carbon.txt file at a given url, and
        if successful, import the carbon.text file
        """
        res = requests.get(url)
        domain = parse.urlparse(url).netloc
        carbon_txt_string = res.content.decode("utf-8")

        return self.parse_and_import(domain, carbon_txt_string)
