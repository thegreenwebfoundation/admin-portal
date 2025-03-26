import pytest
from guardian.shortcuts import assign_perm

from apps.accounts.permissions import manage_provider
from apps.greencheck.exceptions import NoMatchingDomainHash
from apps.greencheck.models import GreenDomain


@pytest.mark.django_db
class TestGreenDomainClaim:
    """
    This code exercises the "domain claim" functionality in the platform, for
    carrying out a carbon.txt domain validation.
    """

    def test_claim_domain_with_no_domain_hash(self):
        """
        Test that attempting to claim a domain without a corresponding domain hash
        raises a NoMatchingDomainHash exception.
        """
        domain_name = "example.com"

        with pytest.raises(NoMatchingDomainHash):
            GreenDomain.claim_via_carbon_txt(domain_name, provider=None)

    def test_claim_domain_with_via_header(self, user_with_provider, httpx_mock):
        """
        Test that claiming a domain with a valid domain hash in the 'via header'
        is successful.
        """

        managed_service = "managed-service.com"
        hosted_site = "example.com"

        provider = user_with_provider.hosting_providers.first()
        provider.refresh_shared_secret()

        domain_hash = provider.create_domain_hash(hosted_site, user_with_provider)

        httpx_mock.add_response(
            url="https://example.com/carbon.txt",
            headers={"Via": f"{managed_service}/carbon.txt {domain_hash.hash}"},
        )

        resp = GreenDomain.claim_via_carbon_txt(hosted_site, provider)

        assert resp in GreenDomain.objects.filter(hosted_by_id=provider.id)

    def test_claim_domain_with_dns_txt_record(self, user_with_provider, mocker):
        """
        Test that claiming a domain with a valid domain hash as a TXT record in DNS
        is successful.
        """

        # Given: a managed service that operates multiple domains
        provider = user_with_provider.hosting_providers.first()
        provider.refresh_shared_secret()

        # Given: a website operated by the managing service above
        hosted_site = "delegating-with-txt-record.carbontxt.org"

        # And: the website has been associated with the provider
        domain_hash = provider.create_domain_hash(hosted_site, user_with_provider)

        # And DNS record has been set up for the domain with the correct hash added
        # as a TXT record, and pointing to the managing service's carbon.txt file
        mocker.patch(
            "apps.greencheck.domain_check.GreenDomainChecker._lookup_domain_hash_with_dns",
            return_value=f"managed-service.com/carbon.txt {domain_hash.hash}",
        )

        # When: the managing service posts a request to verify the domain hash
        # has been added to the domain's DNS record
        resp = GreenDomain.claim_via_carbon_txt(hosted_site, provider)

        # Then: the domain show up as associated with the managed service provider
        assert resp in GreenDomain.objects.filter(hosted_by_id=provider.id)

    def test_claim_domain_with_two_competing_providers(
        self, user_with_provider, hosting_provider_factory, user_factory, mocker
    ):
        """
        We want to make sure that when we have two providers both trying to claim a
        domain, we allocate the domain to the correct provider, based on the
        domain hash found, not just the most recent provider to request.
        """

        # Given: one 'correct' hosting provider
        correct_provider = user_with_provider.hosting_providers.first()
        correct_provider.refresh_shared_secret()

        # And: a 'sneaky' provider with a different user
        sneaky_user = user_factory()
        sneaky_provider = hosting_provider_factory(created_by=sneaky_user)
        sneaky_provider.refresh_shared_secret()
        assign_perm(manage_provider.codename, sneaky_user, sneaky_provider)

        # And: a website that both providers want to claim
        hosted_site = "site-with-competing-claims.example.com"

        # And: both providers created domain hashes for the site
        correct_domain_hash = correct_provider.create_domain_hash(
            hosted_site, user_with_provider
        )
        domain_hash_2 = sneaky_provider.create_domain_hash(hosted_site, sneaky_user)

        # When: the DNS record contains correct_provider's domain_hash
        mocker.patch(
            "apps.greencheck.domain_check.GreenDomainChecker._lookup_domain_hash_with_dns",
            return_value=f"correct_provider.example.com/carbon.txt {correct_domain_hash.hash}",
        )

        # Then: even when both providers try to claim the domain
        resp = GreenDomain.claim_via_carbon_txt(hosted_site, correct_provider)
        resp2 = GreenDomain.claim_via_carbon_txt(hosted_site, sneaky_provider)

        # The domain should be associated with just the correct provider,
        # as its hash was found
        assert resp in GreenDomain.objects.filter(hosted_by_id=correct_provider.id)
        assert resp not in GreenDomain.objects.filter(hosted_by_id=sneaky_provider.id)
