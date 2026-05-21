import logging

import pytest
from corsheaders.middleware import ACCESS_CONTROL_ALLOW_ORIGIN
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from ...accounts import models as ac_models

User = get_user_model()

pytestmark = pytest.mark.django_db

logger = logging.getLogger(__name__)

rf = APIRequestFactory()

class TestCORSforAPI:
    def test_requests_have_permissive_cors_enabled_for_api(
        self, hosting_provider_with_sample_user: ac_models.Hostingprovider, client
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
