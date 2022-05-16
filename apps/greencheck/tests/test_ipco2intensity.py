import logging
import pytest

from django.urls import reverse
from rest_framework.test import APIRequestFactory

from .. import models as gc_models
from .. import viewsets as gc_viewsets
from .. import api
from .. import serializers


pytestmark = pytest.mark.django_db

logger = logging.getLogger(__name__)

rf = APIRequestFactory()


class TestIPCO2IntensityViewGet:
    def test_get_ip_empty(self):
        """
        Exercise the simplest happy path - we return a payload listing the IP
        for the given IP address
        """

        rf = APIRequestFactory()
        url_path = reverse("ip-to-co2intensity")
        request = rf.get(url_path)

        # GET end point for IP Ranges
        view_func = api.views.IPCO2Intensity.as_view()

        response = view_func(request)

        # check contents
        assert response.status_code == 200

    def test_get_specific_ip(self,):
        """
        Check with a specific IP to lookup.
        """
        ip_to_check = "85.17.184.227"

        url_path = reverse("ip-to-co2intensity", kwargs={"ip_to_check": ip_to_check})

        # This uses the API client as the APIRequestFactory does
        # not seem to honor the kwargs passed in
        from rest_framework.test import APIClient

        client = APIClient()

        # rf = APIRequestFactory()
        # view_func = api.views.IPCO2Intensity.as_view()
        # request = rf.get(url_path)

        # GET end point for IP Ranges
        response = client.get(url_path)
        # response = view_func(request)

        # check contents
        assert response.status_code == 200

        assert response.data.get("checked_ip") == ip_to_check


class TestIPCO2IntensitySerializer:
    def test_serialize_ip_lookup(self):

        payload = {
            "city": "Mountain View",
            "country_code": "US",
            "country_name": "United States",
            "annual_avg_co2_intensity": 123.12,
        }

        serialized = serializers.CO2ItensitySerializer(payload)

        fields = [
            "country_code",
            "country_name",
            "city",
            "annual_avg_co2_intensity",
        ]

        for field in fields:
            assert field in serialized.data
