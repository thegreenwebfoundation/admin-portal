import logging

from django.contrib.gis.geoip2 import GeoIP2
from geoip2 import errors

from rest_framework import views
from rest_framework import permissions
from rest_framework.response import Response
from ..serializers import CO2ItensitySerializer

from django.conf import settings

logger = logging.getLogger(__name__)

geolookup = GeoIP2(settings.GEOIP_PATH)


class IPCO2Intensity(views.APIView):
    """
    A view to return the CO2e intensity a given IP address.

    The IP address is provided by either the requesting IP,
    or provided as single parameter.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = CO2ItensitySerializer

    def extract_ip(self, request):
        # TODO look a provided IP in data, to allow clients to
        # specificy an IP to look up specfically

        return request.META.get("REMOTE_ADDR")

    def lookup_ip(self, ip_to_trace=None):

        res = None

        try:
            res = geolookup.city(ip_to_trace)
        except errors.AddressNotFoundError:
            # Give a fallback value to global defaults
            # if no usable result is returned
            res = {
                "city": "Unknown",
                "country_code": "XX",
                "country_name": "World",
                "annual_avg_co2_intensity": 442,
            }

        return res

    def get(self, request, format=None):
        """
        Return the CO2 intensity for the IP address
        """

        ip_address = self.extract_ip(request)
        ip_lookup_res = self.lookup_ip(ip_address)

        serialized = CO2ItensitySerializer(ip_lookup_res)
        return Response(serialized.data)
