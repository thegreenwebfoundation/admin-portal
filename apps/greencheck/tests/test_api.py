import logging

import pytest
from corsheaders.conf import conf
from corsheaders.middleware import ACCESS_CONTROL_ALLOW_ORIGIN
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.authtoken import models, views
from rest_framework.test import APIRequestFactory

from ..models import Hostingprovider
from ..viewsets import GreenDomainViewset

User = get_user_model()

pytestmark = pytest.mark.django_db

logger = logging.getLogger(__name__)

rf = APIRequestFactory()


class TestUsingAuthToken:
    def test_fetching_auth_token(
        self, hosting_provider: Hostingprovider, sample_hoster_user: User,
    ):
        """
        Anyone who is able to update an organisation is able to
        generate an API token.
        """
        hosting_provider.save()
        sample_hoster_user.hostingprovider = hosting_provider
        sample_hoster_user.save()

        # set up our views, request factories and paths
        rf = APIRequestFactory()
        url_path = reverse("api-obtain-token")
        view = views.ObtainAuthToken.as_view()

        # create our request
        credentials = {"username": sample_hoster_user.username, "password": "topSekrit"}
        request = rf.post(url_path, credentials)

        response = view(request)
        token = models.Token.objects.get(user=sample_hoster_user)

        # check contents, is the token the right token?
        assert response.status_code == 200
        assert response.data["token"] == token.key


class TestCORSforAPI:
    def test_requests_have_permissive_cors_enabled_for_api(
        self, hosting_provider_with_sample_user: Hostingprovider, client
    ):
        """
        Are we serving CORS enabled requests, so that browser extensions can
        look up domains easily?
        """

        # url_path = reverse("green-domain-detail", kwargs={"url": "google.com"})
        url_path = reverse("green-domain-list")

        # create our request, without our origin,
        # we don't have any access control responses
        response = client.get(url_path, HTTP_ORIGIN="http://example.com")

        # do we have working response?
        assert response.status_code == 200

        # do we have the expected header to allow cross domain API calls?
        assert ACCESS_CONTROL_ALLOW_ORIGIN in response
        assert response[ACCESS_CONTROL_ALLOW_ORIGIN] == "*"

