import logging
import pytest

from django.urls import reverse
from rest_framework.test import APIRequestFactory

from .. import api
from .. import serializers
from .. import models


pytestmark = pytest.mark.django_db

logger = logging.getLogger(__name__)

rf = APIRequestFactory()
from ..models import CO2Intensity


class TestIPCO2IntensityViewGet:
    def test_get_ip_empty(self, mocker):
        """
        Exercise the simplest happy path - we return a payload listing the IP
        for the given IP address
        """

        # we mock this call to avoid needing to download the GeoIP binary
        # database in our tests
        mocker.patch(
            "apps.greencheck.api.views.IPCO2Intensity.lookup_ip",
            return_value=CO2Intensity.global_value(),
        )

        rf = APIRequestFactory()
        url_path = reverse("ip-to-co2intensity")
        request = rf.get(url_path)

        # GET end point for IP Ranges
        view_func = api.views.IPCO2Intensity.as_view()

        response = view_func(request)

        # check contents
        assert response.status_code == 200

    def test_get_specific_ip(self, mocker):
        """
        Check with a specific IP to lookup.
        """

        # we mock this call to avoid needing to download the GeoIP binary
        # database in our tests
        mocker.patch(
            "apps.greencheck.api.views.IPCO2Intensity.lookup_ip",
            return_value=CO2Intensity.global_value(),
        )

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
            "country_name": "World",
            "country_code_iso_2": "xx",
            "country_code_iso_3": "xxx",
            "carbon_intensity_type": "avg",
            "carbon_intensity": models.checks.GLOBAL_AVG_CO2_INTENSITY,
            "generation_from_fossil": models.checks.GLOBAL_AVG_FOSSIL_SHARE,
            "year": 2021,
        }

        serialized = serializers.CO2IntensitySerializer(payload)

        fields = [
            "country_code_iso_2",
            "country_code_iso_3",
            "carbon_intensity_type",
            "carbon_intensity",
            "generation_from_fossil",
            "year",
        ]

        for field in fields:
            assert field in serialized.data
