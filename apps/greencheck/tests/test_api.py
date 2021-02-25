import logging

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.authtoken import models, views
from rest_framework.test import APIRequestFactory

from ..models import Hostingprovider

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
