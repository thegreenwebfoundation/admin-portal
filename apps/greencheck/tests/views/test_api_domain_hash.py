import pytest
from apps.accounts.models import DomainHash


class TestDomainHashforProvider:
    """
    Tests for the DomainHash API endpoint.
    """

    @pytest.mark.django_db
    def test_domain_hash_generation(self, client, user_with_provider):
        # Given: A logged-in user associated with a hosting provider
        client.force_login(user_with_provider)
        provider = user_with_provider.hosting_providers.first()
        provider.refresh_shared_secret()

        domain_name = "example.com"
        payload = {"domain": domain_name}

        # When: The user sends a POST request to /api/v3/domain_hash/ with a domain name
        response = client.post(
            "/api/v3/domain_hash/", payload, content_type="application/json"
        )

        # Then: The response should contain a domain hash and the domain name
        assert response.status_code == 200
        response_data = response.json()
        assert "domain_hash" in response_data
        assert response_data["domain_hash"] is not None
        assert response_data["domain"] == domain_name

        # Then: A DomainHash object should be created and persisted in the database
        domain_hash_obj = DomainHash.objects.filter(domain=domain_name).first()
        assert domain_hash_obj is not None
        assert domain_hash_obj.domain == domain_name
        assert response_data["domain_hash"] == domain_hash_obj.hash

    @pytest.mark.django_db
    def test_domain_hash_generation_for_repeated_posts(
        self, client, user_with_provider
    ):
        """
        Tests that repeated POST requests for the same domain return the same hash.
        """
        # Given: A logged-in user associated with a hosting provider
        client.force_login(user_with_provider)
        provider = user_with_provider.hosting_providers.first()
        provider.refresh_shared_secret()

        domain_name = "example.com"
        payload = {"domain": domain_name}

        # When: The user sends a POST request to /api/v3/domain_hash/ with a domain name
        response = client.post(
            "/api/v3/domain_hash/", payload, content_type="application/json"
        )
        # When: The user sends another POST request with the same domain name
        repeat_response = client.post(
            "/api/v3/domain_hash/", payload, content_type="application/json"
        )

        # Then: Only one DomainHash object should be created in the database
        domain_hash_matches = DomainHash.objects.filter(domain=domain_name)
        assert len(domain_hash_matches) == 1
        domain_hash_obj = domain_hash_matches.first()

        assert domain_hash_obj is not None
        assert domain_hash_obj.domain == domain_name

        # Then: Both responses should contain the same domain hash and domain name
        for resp in [response, repeat_response]:
            assert resp.status_code == 200
            resp_data = resp.json()
            assert "domain_hash" in resp_data
            assert resp_data["domain_hash"] is not None
            assert resp_data["domain"] == domain_name
            assert resp_data["domain_hash"] == domain_hash_obj.hash
