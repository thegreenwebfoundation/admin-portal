import logging
import pytest
import pathlib

from django.urls import reverse
from rest_framework.test import APIRequestFactory

from ... import api
import apps.accounts.models as ac_models

from ... import exceptions


pytestmark = pytest.mark.django_db

logger = logging.getLogger(__name__)

rf = APIRequestFactory()


@pytest.fixture
def carbon_txt_string():
    pth = pathlib.Path(__file__)

    carbon_txt_path = pth.parent.parent / "carbon-txt-samples" / "carbon-txt-test.toml"

    carbon_txt_string = None
    with open(carbon_txt_path) as carb_file:
        carbon_txt_string = carb_file.read()

    return carbon_txt_string


class TestCarbonTxtAPI:
    def test_carbon_txt_url_and_content(
        self,
        db,
        carbon_txt_string,
        hosting_provider_factory,
        supporting_evidence_factory,
        green_domain_factory,
    ):
        """Check our seriliasation works"""
        provider = hosting_provider_factory.create(
            name="www.hillbob.de", website="https://www.hillbob.de"
        )
        supporting_evidence_factory.create(hostingprovider=provider)

        # create our upstream providers
        systen_upstream = hosting_provider_factory.create(
            name="sys-ten.com", website="https://sys-ten.com"
        )
        supporting_evidence_factory.create(
            hostingprovider=systen_upstream,
            url="https://www.sys-ten.de/en/about-us/our-data-centers/",
        )

        cdn_upstream = hosting_provider_factory.create(
            name="cdn.com", website="https://cdn.com"
        )
        supporting_evidence_factory.create(
            hostingprovider=cdn_upstream,
            url="https://cdn.com/company/corporate-responsibility/sustainability",
        )

        # create our domains we use to look up each provider
        green_domain_factory.create(hosted_by=provider, url="www.hillbob.de")
        green_domain_factory.create(hosted_by=systen_upstream, url="sys-ten.com")
        green_domain_factory.create(hosted_by=cdn_upstream, url="cdn.com")

        url_path = reverse("carbon-txt-parse")
        request = rf.put(
            url_path,
            {
                "url": "https://www.hillbob.de/carbon.txt",
                "carbon_txt": carbon_txt_string,
            },
        )

        # PUT end point for testing carbontxt
        view_func = api.views.CarbonTxtAPI.as_view()

        response = view_func(request)

        assert response.status_code == 200


class TestProviderSharedSecretAPI:
    """
    Some of our carbon txt parsers rely on shared secrets to establish a link
    between two domains. This API exposes the ablity to create shared secrets,
    fetch them, and reset them if needed.
    """

    def test_fetching_shared_secret_with_none_set(
        self,
        db,
        hosting_provider_with_sample_user: ac_models.Hostingprovider,
    ):
        """
        Check that when no secret secret is set, we provide a helpful error message.
        """

        # Given: a provider and user able to sign in with their credentials
        url_path = reverse("carbon-txt-shared-secret")
        provider = hosting_provider_with_sample_user
        user = provider.users.first()
        view_func = api.views.ProviderSharedSecretView.as_view()

        # When: a user tries to fetch the token
        request = rf.get(url_path)
        request.user = user
        response = view_func(request)

        # No token is served because it hasn't been created
        assert response.status_code == 404
        assert (
            exceptions.NoSharedSecret.default_detail
            in response.render().content.decode("utf-8")
        )

    def test_fetching_shared_secret_with_secret_set(
        self,
        db,
        hosting_provider_with_sample_user: ac_models.Hostingprovider,
    ):
        """
        Check that fetching our shared_secret is possible for signed in users
        """

        # Given: a provider and user able to sign in with their credentials
        url_path = reverse("carbon-txt-shared-secret")
        view_func = api.views.ProviderSharedSecretView.as_view()
        provider = hosting_provider_with_sample_user
        user = provider.users.first()

        # And: a generated shared secret
        provider.refresh_shared_secret()

        # When: they request the shared secret
        request = rf.get(url_path)
        request.user = user
        response = view_func(request)

        # then: they should see the token for them to use
        assert response.status_code == 200
        assert provider.shared_secret.body in response.render().content.decode("utf-8")

    def test_resetting_shared_secret(
        self,
        db,
        hosting_provider_with_sample_user: ac_models.Hostingprovider,
    ):
        """
        Check we can reset our shared secret, and fetch it when needed
        """

        # given: a provider and user able to sign in with their credentials
        url_path = reverse("carbon-txt-shared-secret")
        view_func = api.views.ProviderSharedSecretView.as_view()
        provider = hosting_provider_with_sample_user
        user = provider.users.first()

        # when: the user visits their provider with no shared_secret set
        request = rf.get(url_path)
        request.user = user
        response = view_func(request)
        # then: no token should be served

        assert response.status_code == 404

        # when our user resets their token
        reset_token_request = rf.post(url_path)
        reset_token_request.user = user
        reset_token_response = view_func(reset_token_request)

        # then: they should see the generated token
        assert reset_token_response.status_code == 200
        assert (
            provider.shared_secret.body
            in reset_token_response.render().content.decode("utf-8")
        )

        # and: when they visit later
        fetch_token_request = rf.get(url_path)
        fetch_token_request.user = user
        fetch_token_response = view_func(fetch_token_request)

        # then: they should see the same token
        assert fetch_token_response.status_code == 200
        assert (
            provider.shared_secret.body
            in fetch_token_response.render().content.decode("utf-8")
        )
