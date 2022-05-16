import logging

from django.contrib.gis.geoip2 import GeoIP2
from django.contrib.gis.geoip2.base import GeoIP2Exception

from apps.greencheck.models.checks import CO2Intensity
from geoip2 import errors

from rest_framework import views
from rest_framework import permissions
from rest_framework.response import Response
from ..serializers import CO2IntensitySerializer

from django.conf import settings

logger = logging.getLogger(__name__)


geolookup = None

try:
    geolookup = GeoIP2(settings.GEOIP_PATH)
except GeoIP2Exception as e:
    logger.warning(
        "No valid path found for the GeoIp binary database. "
        "We will not be able to serve ip-to-co2-intensity lookups."
    )



class IPCO2Intensity(views.APIView):
    """
    A view to return the CO2e intensity a given IP address.

    The IP address is provided by either the requesting IP,
    or provided as single parameter.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = CO2IntensitySerializer

    def extract_ip(self, request, ip_to_check):
        """
        Return either the IP used for the connection,
        or the one explicitly provided in the API
        """

        if ip_to_check:
            return ip_to_check

        # otherwise fallback to the originating IP
        return request.META.get("REMOTE_ADDR")

    def lookup_ip(self, ip_to_trace=None):
        """
        Lookup a carbon intensity result for the given IP, based
        on the country the IP is estimated to reside in.
        Fall back to a global average if we can't find more specific
        geolocation info.
        """

        # exit early if we do not have access to our `geolookup`
        # GeoIP lookup service
        if not geolookup:
            return CO2Intensity.global_value()

        res = None
        try:
            res = geolookup.city(ip_to_trace)
        except errors.AddressNotFoundError:
            logger.info("No matching result for the provided IP")

        if res is not None:
            country_code = res.get("country_code")
            return CO2Intensity.check_for_country_code(country_code)

        # we couldn't trace this to a given country, fallback to default 'world' value
        return CO2Intensity.global_value()

    def get(self, request, ip_to_check=None, format=None):
        """
        Return the CO2 intensity for the IP address
        """
        ip_address = self.extract_ip(request, ip_to_check)
        ip_lookup_res = self.lookup_ip(ip_address)

        serialized = CO2IntensitySerializer(
            ip_lookup_res, context={"checked_ip": ip_address}
        )
        return Response(serialized.data)
