import pytest

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

        payload = {"domain": domain}

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
    def test_domain_claim_for_an_already_claimed_domain_by_a_provider(
        self, client, user_with_provider, mocker, hosting_provider_factory, user_factory
    ):
        """
        When a different provider is able to demonstrate control over a domain
        we reallocate the domain to them.
        """
        from apps.accounts.permissions import manage_provider
        from guardian.shortcuts import assign_perm

        # Ideally this would rely on us being able to order green domains by
        # created date. That would leave us with an audit trail of claimed domains
        # rather than overwiting them with the most recent claim.

        # Given: A logged-in user associated with a hosting provider
        client.force_login(user_with_provider)
        provider = user_with_provider.hosting_providers.first()
        provider.refresh_shared_secret()

        # and a new user managing a new provider
        new_user = user_factory.create()
        new_provider = hosting_provider_factory.create(created_by=new_user)
        assign_perm(manage_provider.codename, new_user, new_provider)
        new_provider.refresh_shared_secret()

        # when both providers have requested a domain hash
        domain = "example.com"
        domain_hash = provider.create_domain_hash(domain, user_with_provider)
        # breakpoint()
        # new_domain_hash = new_provider.create_domain_hash(domain, new_user)

        # and the first domain hash is associated with the first provider
        mocker.patch(
            "apps.greencheck.domain_check.GreenDomainChecker._lookup_domain_hash_with_dns",
            return_value=f"{domain}/carbon.txt {domain_hash.hash}",
        )
        # mocker.patch(
        #     "apps.greencheck.domain_check.GreenDomainChecker._lookup_domain_hash_with_dns",
        #     side_effect=[
        #         f"{provider.website_domain}/carbon.txt {domain_hash.hash}",
        #         f"{new_provider.website_domain}/carbon.txt {new_domain_hash.hash}",
        #     ],
        # )

        # TODO the problem we have here is that claim via carbon_txt
        # needs to be able to differentiate between the two providers
        # to know which provider to associated it with.
        # when we only use the domain, we can't tell, so we the method
        # also needs to take the provider as an argument, so we
        # can tell which domain hash we are looking for.

        resp = GreenDomain.claim_via_carbon_txt(domain)
        assert resp in GreenDomain.objects.filter(url=domain)

        # we now need to simulate the domain being updated and new result coming back
        # GreenDomain.create_for_provider(domain)
        # assert GreenDomain.objects.filter(url=domain).count() == 2
