import pytest
from django.urls import reverse

from apps.accounts import models as ac_models


@pytest.mark.django_db
class TestLinkedProviderAutocompleteView:
    def test_unauthenticated_user_gets_empty_results(self, client):
        """Given an unauthenticated user, when they hit the autocomplete, they get no results."""
        url = reverse("linked-provider-autocomplete")
        response = client.get(url)

        assert response.status_code == 200
        assert response.json()["results"] == []

    def test_authenticated_user_sees_active_listed_providers(self, client, sample_hoster_user):
        """Given an authenticated user, when they hit the autocomplete, they see active listed providers."""
        provider = ac_models.Hostingprovider.objects.create(
            name="Green Provider",
            country="GB",
            archived=False,
            is_listed=True,
            website="https://example.com",
        )
        url = reverse("linked-provider-autocomplete")
        client.force_login(sample_hoster_user)
        response = client.get(url)

        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 1
        assert results[0]["text"] == "Green Provider"

    def test_archived_providers_excluded(self, client, sample_hoster_user, hosting_provider_factory):
        """Given archived providers exist, they should not appear in autocomplete results."""
        hosting_provider_factory.create(name="Archived Provider", archived=True, is_listed=True)
        url = reverse("linked-provider-autocomplete")
        client.force_login(sample_hoster_user)
        response = client.get(url)

        assert response.status_code == 200
        results = response.json()["results"]
        assert all("Archived" not in r["text"] for r in results)

    def test_unlisted_providers_excluded(self, client, sample_hoster_user, hosting_provider_factory):
        """Given unlisted providers exist, they should not appear in autocomplete results."""
        hosting_provider_factory.create(name="Unlisted Provider", archived=False, is_listed=False)
        url = reverse("linked-provider-autocomplete")
        client.force_login(sample_hoster_user)
        response = client.get(url)

        assert response.status_code == 200
        results = response.json()["results"]
        assert all("Unlisted" not in r["text"] for r in results)

    def test_all_countries_returned_when_no_country_forwarded(self, client, sample_hoster_user, hosting_provider_factory):
        """Given no country is forwarded, providers from all countries are returned."""
        uk_provider = hosting_provider_factory.create(
            name="UK Provider", country="GB", archived=False, is_listed=True
        )
        us_provider = hosting_provider_factory.create(
            name="US Provider", country="US", archived=False, is_listed=True
        )

        url = reverse("linked-provider-autocomplete")
        client.force_login(sample_hoster_user)
        response = client.get(url)

        assert response.status_code == 200
        results = response.json()["results"]
        texts = [r["text"] for r in results]
        assert "UK Provider" in texts
        assert "US Provider" in texts

    def test_results_ordered_by_name(self, client, sample_hoster_user, hosting_provider_factory):
        """Given multiple providers, results are ordered alphabetically by name."""
        hosting_provider_factory.create(name="Zebra Hosting", country="GB", archived=False, is_listed=True)
        hosting_provider_factory.create(name="Alpha Hosting", country="GB", archived=False, is_listed=True)

        url = reverse("linked-provider-autocomplete")
        client.force_login(sample_hoster_user)
        response = client.get(url)

        assert response.status_code == 200
        results = response.json()["results"]
        texts = [r["text"] for r in results]
        assert texts == sorted(texts)

    def test_search_filters_by_name_prefix(self, client, sample_hoster_user, hosting_provider_factory):
        """Given a search term, only matching providers are returned."""
        hosting_provider_factory.create(name="Green Web", country="GB", archived=False, is_listed=True)
        hosting_provider_factory.create(name="Grey Web", country="GB", archived=False, is_listed=True)

        url = reverse("linked-provider-autocomplete")
        client.force_login(sample_hoster_user)
        response = client.get(url, {"q": "Green"})

        assert response.status_code == 200
        results = response.json()["results"]
        texts = [r["text"] for r in results]
        assert "Green Web" in texts
        assert "Grey Web" not in texts


@pytest.mark.django_db
class TestProviderAutocompleteView:
    def test_unauthenticated_user_gets_empty_results(self, client):
        """
        Given an unauthenticated user,
        when they hit the provider autocomplete endpoint,
        then they get an empty result set and no 500 error is raised.
        """
        url = reverse("provider-autocomplete")
        response = client.get(url)

        assert response.status_code == 200
        assert response.json()["results"] == []


@pytest.mark.django_db
class TestLabelAutocompleteView:
    def test_unauthenticated_user_gets_empty_results(self, client):
        """
        Given an unauthenticated user,
        when they hit the label autocomplete endpoint,
        then they get an empty result set and no 500 error is raised.
        """
        url = reverse("label-autocomplete")
        response = client.get(url)

        assert response.status_code == 200
        assert response.json()["results"] == []
