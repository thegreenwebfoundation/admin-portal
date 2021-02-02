import logging
import ipaddress

import pytest

from django.urls import reverse
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import Group, Permission

from rest_framework.test import RequestsClient, APIClient
from rest_framework.authtoken.models import Token
from rest_framework import serializers

from django.contrib.auth import get_user_model
from apps.greencheck.models import Hostingprovider
from apps.greencheck.viewsets import IPRangeViewSet

User = get_user_model()

pytestmark = pytest.mark.django_db

logger = logging.getLogger(__name__)

rf = APIRequestFactory()


@pytest.mark.only
class TestIpRangeViewSetList:
    def test_get_ip_ranges_empty(
        self, hosting_provider: Hostingprovider, sample_hoster_user: User,
    ):
        """
        Exercise the simplest happy path.
        """

        hosting_provider.save()
        sample_hoster_user.hostingprovider = hosting_provider
        sample_hoster_user.save()

        rf = APIRequestFactory()
        url_path = reverse("ip-range-list")
        request = rf.get(url_path)
        request.user = sample_hoster_user

        # GET end point for IP Ranges
        view = IPRangeViewSet.as_view({"get": "list"})

        response = view(request)

        # check contents
        assert response.status_code == 200
        assert len(response.data) == 0

    @pytest.mark.skip
    def test_get_ip_ranges_for_hosting_with_ranges(self):
        pass

    def test_get_ip_ranges_without_auth(
        self, hosting_provider: Hostingprovider, sample_hoster_user: User,
    ):
        hosting_provider.save()
        sample_hoster_user.hostingprovider = hosting_provider
        sample_hoster_user.save()

        rf = APIRequestFactory()
        url_path = reverse("ip-range-list")
        request = rf.get(url_path)

        # set up the viewset, as a views, so it knows what to do when we
        # pass in a GET request as defined a couple of lines up
        view = IPRangeViewSet.as_view({"get": "list"})

        # ipdb.set_trace()
        # has_permission = permission.has_permission(request, None)
        # import ipdb

        # ipdb.set_trace()
        response = view(request)

        # check contents
        assert response.status_code == 403
        # assert len(response.data) == 0

    def test_get_ip_range_for_user_with_no_hosting_provider(
        self, sample_hoster_user: User, rf: RequestFactory,
    ):
        sample_hoster_user.save()

        rf = APIRequestFactory()
        url_path = reverse("ip-range-list")
        request = rf.get(url_path)
        request.user = sample_hoster_user

        # GET end point for IP Ranges
        view = IPRangeViewSet.as_view({"get": "list"})
        response = view(request)

        # check contents
        assert response.status_code == 200
        assert len(response.data) == 0


@pytest.mark.only
class TestIpRangeViewSetRetrieve:
    """
    """
