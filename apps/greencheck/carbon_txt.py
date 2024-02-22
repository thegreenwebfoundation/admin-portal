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

from . import exceptions


class NoCarbonTxtFileException(Exception):
    pass


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
            logger.debug(f"New supporting doc {doc} for {prov}")

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
            provider_url = prov.get("url")
            if provider_url not in evidence_links:
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

        shared_secret = provider.shared_secret

        # return early if there is no shared secret to check
        if not shared_secret:
            return False

        res = hashlib.sha256(f"{domain}{shared_secret.body}".encode("utf-8"))
        return res.hexdigest() == hash

    def _add_domain_if_hash_matches_provider(
        self, new_domain, provider_domain, domain_hash
    ):
        """
        Accept a new domain we have not seen before with its corresponding hash, plus
        a domain for a known provider, to we can check the domain hash and new domain
        for the known provider.

        Link the new domain to our provider if we have a match, so subsequent lookups
        show as green.
        """
        try:
            matched_domain_hash = self._check_domain_hash_against_provider(
                domain_hash, provider_domain
            )

            if matched_domain_hash:
                # create our new domain
                provider = gc_models.GreenDomain.objects.get(
                    url=provider_domain
                ).hosting_provider

                gc_models.GreenDomain.upsert_for_provider(new_domain, provider)
        except Exception as ex:
            logger.exception(
                f"Unable to create the green domain for: {new_domain} - {ex}"
            )

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
        results = {"org": None, "upstream": {}, "not_registered": {}}

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

                primary_domain = primary_creds.get("domain")
                if primary_domain:
                    results["org"] = {primary_domain: org_provider}
                else:
                    results["org"] = {domain: org_provider}
            # either list as known provider, or add to the list
            # of new entities we do not have in our system yet

            else:
                results["not_registered"]["org"] = org

        # now do the same for upstream providers
        upstream = parsed_txt.get("upstream")
        if upstream:
            upstream_providers = upstream.get("providers")
            unregistered_providers = {}

            for provider in upstream_providers:
                found_provider = self._fetch_provider(provider)
                if found_provider:
                    new_evidence = self._compare_evidence(found_provider, [provider])

                    if new_evidence:
                        unregistered_evidence.extend(new_evidence)

                    if isinstance(provider, str):
                        results["upstream"][provider] = found_provider
                    if isinstance(provider, dict):
                        results["upstream"][provider["domain"]] = found_provider

                else:
                    if isinstance(provider, str):
                        unregistered_providers[provider] = provider

                    if isinstance(provider, dict):
                        unregistered_providers[provider["domain"]] = provider

            if unregistered_evidence:
                results["not_registered"]["evidence"] = unregistered_evidence

            results["not_registered"]["providers"] = unregistered_providers

        return results

    def _check_for_carbon_txt_dns_record(
        self, domain: str, lookup_sequence: List
    ) -> Union[List[str], List]:
        try:
            answers = dns.resolver.resolve(domain, "TXT")
        except dns.resolver.NoAnswer:
            return [None, lookup_sequence]

        if not lookup_sequence:
            lookup_sequence = [{"reason": "Initial domain looked up", "url": domain}]

        override_url = None

        for answer in answers:
            txt_record = answer.to_text().strip('"')
            if txt_record.startswith("carbon-txt"):
                # pull out our url to check
                _, txt_record_body = txt_record.split("=")

                domain_hash_check = txt_record_body.split(" ")

                if len(domain_hash_check) == 1:
                    override_url = domain_hash_check[0]
                    lookup_sequence.append(
                        {"reason": "Delegated via DNS TXT record", "url": override_url}
                    )

                if len(domain_hash_check) == 2:
                    override_url = domain_hash_check[0]
                    domain_hash = domain_hash_check[1]

                    lookup_sequence.append(
                        {"reason": "Delegated via DNS TXT record", "url": override_url}
                    )
                    override_domain = parse.urlparse(override_url).netloc

                    self._add_domain_if_hash_matches_provider(
                        domain, override_domain, domain_hash
                    )

        return override_url, lookup_sequence

    def _check_for_carbon_txt_via_header(
        self, res, lookup_sequence: List = None
    ) -> Union[List[str], List]:
        """
        Look for a HTTP header we can use
        """
        original_url = lookup_sequence[0]["url"]
        original_domain = parse.urlparse(original_url).netloc

        # return early with original request if we see no new headers
        if "via" not in res.headers.keys():
            return [res, lookup_sequence]

        via_header_payload = res.headers["via"].split(" ")

        if len(via_header_payload) == 2:
            protocol, via_url = via_header_payload
            lookup_sequence.append(
                {"reason": "Delegated via HTTP 'via:' header", "url": via_url}
            )
            res = requests.get(via_url)

        if len(via_header_payload) == 3:
            protocol, via_url, domain_hash = via_header_payload
            lookup_sequence.append(
                {"reason": "Delegated via HTTP 'via:' header", "url": via_url}
            )
            res = requests.get(via_url)

        via_domain = parse.urlparse(via_url).netloc

        if domain_hash:
            self._add_domain_if_hash_matches_provider(
                original_domain, via_domain, domain_hash
            )

        return res, lookup_sequence

    def parse_from_url(self, url: str):
        """
        Try to fetch a carbon.txt file at a given url, and
        if successful, returned the parsed view after carrying
        out lookups
        """

        parsed = parse.urlparse(url)
        url_domain = parsed.netloc

        lookup_sequence = []
        lookup_sequence.append({"reason": "Initial URL provided ", "url": url})

        # do a DNS lookup to see if we have a carbon.txt file at a new url we
        # delegating to instead
        override_url, lookup_sequence = self._check_for_carbon_txt_dns_record(
            url_domain, lookup_sequence
        )

        if override_url:
            res = requests.get(override_url)
            url_domain = parse.urlparse(override_url).netloc

        else:
            res = requests.get(url)

        # Not every server serves missing pages as 404 if there is no carbon.txt to fetch.

        # We can't rely on status codes giving a 404, so we use the existence of a TOML
        # file as a proxy check, before falling back to looking in our header file below
        try:
            carbon_txt_string = res.content.decode("utf-8")

            # if we can parse TOML, we assume this is file we can try parsing for
            # carbon.txt specific elements
            parsed_txt = toml.loads(carbon_txt_string)
            parsed_carbon_txt = self.parse(url_domain, carbon_txt_string)
            parsed_carbon_txt["lookup_sequence"] = lookup_sequence
            parsed_carbon_txt["original_string"] = carbon_txt_string
            return parsed_carbon_txt
        except toml.TomlDecodeError:
            logger.warning(f"Unable to parse carbon.txt file at {res.url}")
        except Exception as ex:
            logger.warning(f"ex")
            logger.warning(
                f"Unable to parse carbon.txt file at {res.url}. "
                "We found valid TOML, but we could not parse the contents."
            )

        # check if we are delegating via an HTTP header, as a final fallback
        res, lookup_sequence = self._check_for_carbon_txt_via_header(
            res, lookup_sequence
        )

        try:
            carbon_txt_string = res.content.decode("utf-8")
            parsed_carbon_txt = self.parse(url_domain, carbon_txt_string)
            parsed_carbon_txt["lookup_sequence"] = lookup_sequence
            parsed_carbon_txt["original_string"] = carbon_txt_string
            return parsed_carbon_txt
        except Exception as ex:
            logger.exception(ex)

        # We found no useable file, say so.
        raise exceptions.CarbonTxtFileNotFound

    def parse_and_import(self, domain: str = None, carbon_txt: str = None) -> Dict:
        """
        Accept a domain representing where the carbon.txt file
        comes form, and a string containing the carbon.txt
        contents, and import the organisations listed, returning
        the providers
        """

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
