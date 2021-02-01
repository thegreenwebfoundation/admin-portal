import logging
import ipaddress

import pytest

from django.test import RequestFactory
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


@pytest.mark.only
class TestIpRangeViewSetList:

    # instantiate viewset
    view = IPRangeViewSet()

    def test_get_ip_ranges_empty(
        self,
        hosting_provider: Hostingprovider,
        sample_hoster_user: User,
        rf: RequestFactory,
    ):
        """
        Exercise the simplest happy path.
        """

        hosting_provider.save()
        sample_hoster_user.hostingprovider = hosting_provider
        sample_hoster_user.save()

        request = rf.get(f"/api/v2/ip-ranges/")
        request.user = sample_hoster_user

        # GET end point for IP Ranges
        response = self.view.list(request)

        # check contents
        assert response.status_code == 200
        assert len(response.data) == 0

    @pytest.mark.skip
    def test_get_ip_ranges_for_hosting_with_ranges(self):
        pass

    @pytest.mark.skip
    def test_get_ip_ranges_without_auth(self):
        pass

    def test_get_ip_range_for_user_with_no_hosting_provider(
        self, sample_hoster_user: User, rf: RequestFactory,
    ):
        sample_hoster_user.save()

        request = rf.get(f"/api/v2/ip-ranges/")
        request.user = sample_hoster_user

        # GET end point for IP Ranges
        response = self.view.list(request)

        # check contents
        assert response.status_code == 200
        assert len(response.data) == 0


@pytest.mark.only
class TestIpRangeViewSetRetrieve:
    """
    """
