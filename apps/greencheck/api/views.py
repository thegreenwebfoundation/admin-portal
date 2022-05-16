import logging

from django.contrib.gis.geoip2 import GeoIP2
from apps.greencheck.models.checks import CO2Intensity
from geoip2 import errors

from rest_framework import views
from rest_framework import permissions
from rest_framework.response import Response
from ..serializers import CO2IntensitySerializer

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
    serializer_class = CO2IntensitySerializer

    def extract_ip(self, request):
        # TODO look a provided IP in data, to allow clients to
        # specificy an IP to look up specfically

        return request.META.get("REMOTE_ADDR")

    def lookup_ip(self, ip_to_trace=None):

        try:
            return geolookup.city(ip_to_trace)
        except errors.AddressNotFoundError:
            return None

    def get(self, request, format=None):
        """
        Return the CO2 intensity for the IP address
        """

        ip_address = self.extract_ip(request)
        ip_lookup_res = self.lookup_ip(ip_address)

        res = None
        if ip_lookup_res is None:
            res = CO2Intensity.global_value()
        else:
            country_code = ip_lookup_res.get("country_code")
            res = CO2Intensity.check_for_country_code(country_code)

        serialized = CO2IntensitySerializer(res, context={"checked_ip": ip_address})
        return Response(serialized.data)
