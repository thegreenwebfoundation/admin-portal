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
