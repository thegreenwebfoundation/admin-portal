import pytest
from guardian.shortcuts import assign_perm

from apps.accounts.permissions import manage_provider
from apps.greencheck.models import GreenDomain


class TestDomainclaimForProvider:
    """
    Tests for the domain claim API endpoint, to allow a domain to be 'claimed'
    by a Provider that has already created a domain hash.
    """

    @pytest.mark.django_db
    def test_successful_domain_claim_by_provider(
        self, client, user_with_provider, mocker
    ):
        """
        The happy path for claiming domain once a domain hash has
        been created by a given provider.
        """
        # Given: A logged-in user associated with a hosting provider
        client.force_login(user_with_provider)
        provider = user_with_provider.hosting_providers.first()
        provider.refresh_shared_secret()
        domain = "example.com"

        domain_hash = provider.create_domain_hash(domain, user_with_provider)

        payload = {"domain": domain, "provider": provider.id}

        mocker.patch(
            "apps.greencheck.domain_check.GreenDomainChecker._lookup_domain_hash_with_dns",
            return_value=f"managed-service.com/carbon.txt {domain_hash.hash}",
        )

        # When: The user sends a POST request to /api/v3/domain_claim/ for the domain
        response = client.post(
            "/api/v3/domain_claim/", payload, content_type="application/json"
        )

        # Then: The response should contain a domain, provider and meaningful status
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["domain"] == domain
        assert response_data["provider"] == provider.name
        assert response_data["provider_id"] == provider.id
        assert response_data["provider_website"] == provider.website
        assert response_data["status"] == "claimed"

    @pytest.mark.django_db
    def test_domain_claim_for_an_already_claimed_domain_by_a_provider(
        self, client, user_with_provider, mocker
    ):
        """
        If a domain already exists for that provider it should not be claimed again.
        """
        # Given: A logged-in user associated with a hosting provider
        client.force_login(user_with_provider)
        provider = user_with_provider.hosting_providers.first()
        provider.refresh_shared_secret()
        domain = "example.com"

        domain_hash = provider.create_domain_hash(domain, user_with_provider)

        payload = {"domain": domain}

        mocker.patch(
            "apps.greencheck.domain_check.GreenDomainChecker._lookup_domain_hash_with_dns",
            return_value=f"managed-service.com/carbon.txt {domain_hash.hash}",
        )

        # When: The user sends a POST request to /api/v3/domain_claim/ for the domain
        first_response = client.post(
            "/api/v3/domain_claim/", payload, content_type="application/json"
        )
        # And: a second request is made for the same domain by the same provider
        repeat_response = client.post(
            "/api/v3/domain_claim/", payload, content_type="application/json"
        )

        # Then: Both responses should contain a domain, provider and meaningful status
        for resp in [first_response, repeat_response]:
            assert resp.status_code == 200
            resp_data = resp.json()
            assert resp_data["domain"] == domain
            assert resp_data["provider"] == provider.name
            assert resp_data["provider_id"] == provider.id
            assert resp_data["provider_website"] == provider.website
            assert resp_data["status"] == "claimed"

        # And: we should not have any duplicate domains created in our table
        assert GreenDomain.objects.filter(hosted_by_id=provider.id).count() == 1

    @pytest.mark.django_db
    def test_domain_claim_for_domain_being_transferred(
        self,
        client,
        provider_groups,
        user_with_provider,
        mocker,
        hosting_provider_factory,
        user_factory,
    ):
        """
        When a different provider is able to demonstrate control over a domain
        we reallocate the domain to them.
        """

        # Given: A logged-in user associated with a hosting provider
        client.force_login(user_with_provider)
        provider = user_with_provider.hosting_providers.first()
        provider.refresh_shared_secret()

        # And: a new user managing a new provider that the website is
        # being transferred to
        new_provider_user = user_factory.create()
        new_provider = hosting_provider_factory.create(created_by=new_provider_user)
        new_provider.refresh_shared_secret()

        assign_perm(manage_provider.codename, new_provider_user, new_provider)

        # When: providers have requested a domain hash
        domain = "being-transferred.example.com"
        domain_hash = provider.create_domain_hash(domain, user_with_provider)
        new_domain_hash = new_provider.create_domain_hash(domain, new_provider_user)

        # Setup the mock to return different hashes for successive calls
        dns_lookup_mock = mocker.patch(
            "apps.greencheck.domain_check.GreenDomainChecker._lookup_domain_hash_with_dns"
        )
        dns_lookup_mock.side_effect = [
            f"{domain}/carbon.txt {domain_hash.hash}",
            f"{domain}/carbon.txt {new_domain_hash.hash}",
        ]

        # And: the first domain hash has been successfully with the first provider
        resp = GreenDomain.claim_via_carbon_txt(domain, provider)
        assert resp in GreenDomain.objects.filter(url=domain)
        assert resp.hosted_by == provider.name

        # When: the new provider tries to claim the same domain, and has
        # put their new domain hash on the domain
        resp2 = GreenDomain.claim_via_carbon_txt(domain, new_provider)

        # Then: the domain should be transferred to the new provider
        assert resp2 in GreenDomain.objects.filter(url=domain)
        assert resp2.hosted_by == new_provider.name

        # Verify the mock was called twice with different return values
        assert dns_lookup_mock.call_count == 2
