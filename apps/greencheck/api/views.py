import logging

from django.conf import settings
from django.contrib.gis.geoip2 import GeoIP2, GeoIP2Exception
from drf_yasg.utils import swagger_auto_schema
from geoip2 import errors
from rest_framework import permissions, views
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.response import Response

from apps.accounts.models import DomainHash, Hostingprovider
from apps.greencheck.models.checks import CO2Intensity, GreenDomain

from ..serializers import (
    CO2IntensitySerializer,
    DomainClaimSerializer,
    DomainHashSerializer,
    ProviderSharedSecretSerializer,
)
from . import exceptions

logger = logging.getLogger(__name__)


geolookup = None

try:
    geolookup = GeoIP2(settings.GEOIP_PATH)
except GeoIP2Exception:
    logger.warning(
        "No valid path found for the GeoIp binary database. "
        "We will not be able to serve ip-to-co2-intensity lookups."
    )


from .carbon_txt import CarbonTxtAPI  # noqa


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

    @swagger_auto_schema(tags=["IP Carbon Intensity"])
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


class ProviderSharedSecretView(views.APIView):
    # TODO: come up with a better solution to identify a provider in this API
    serializer_class = ProviderSharedSecretSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]

    @swagger_auto_schema(tags=["Provider Shared Secret"])
    def get(self, request, format=None):
        # implicitly choose a first provider that the user has permissions to manage
        provider = request.user.hosting_providers.first()
        if not provider:
            raise exceptions.NotFound

        shared_secret = provider.shared_secret

        if not shared_secret:
            raise exceptions.NoSharedSecret

        serialized = ProviderSharedSecretSerializer(shared_secret)
        return Response(serialized.data)

    @swagger_auto_schema(tags=["Provider Shared Secret"])
    def post(self, request, format=None):
        # implicitly choose a first provider that the user has permissions to manage
        provider = request.user.hosting_providers.first()
        if not provider:
            raise exceptions.NotFound

        provider.refresh_shared_secret()
        serialized = ProviderSharedSecretSerializer(provider.shared_secret)

        return Response(serialized.data)


class DomainHashView(views.APIView):
    """
    A view to handle the creation and retrieval of domain hashes
    for a given provider and domain. Domain hashes are used to
    uniquely identify a domain associated with a hosting provider.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DomainHashSerializer

    @swagger_auto_schema(tags=["Domain Hash"])
    def post(self, request, format=None):
        """
        Handle POST requests to create or retrieve a domain hash.

        If a domain hash already exists for the given provider and domain,
        it retrieves the latest one. Otherwise, it creates a new domain hash.

        The provider can either be explicitly provided in the request data
        or inferred from the authenticated user's hosting providers.

        Args:
            request: The HTTP request object containing the domain and provider.
            format: The format of the response (optional).

        Returns:
            A Response object containing the serialized domain hash.
        """
        # Get the provider from the request data or fallback to the user's first hosting provider
        provider = request.data.get("provider")
        if not provider:
            provider = request.user.hosting_providers.first()

        # Get the domain from the request data
        domain = request.data.get("domain")
        if not domain:
            # Raise a bad request - we need a domain at the very least
            raise exceptions.BadRequest(
                "A domain must be provided request a domain hash for it."
            )

        # Check if a domain hash already exists for the given provider and domain
        provider_domain_hash_matches = DomainHash.objects.filter(
            domain=domain, provider=provider
        ).order_by("-created")

        if provider_domain_hash_matches.exists():
            # Use the most recently created domain hash if it exists
            domain_hash = provider_domain_hash_matches.first()
        else:
            # Otherwise create a new domain hash
            domain_hash = provider.create_domain_hash(domain=domain, user=request.user)

        # Serialize the domain hash and return it in the response
        serialized = DomainHashSerializer(domain_hash)

        return Response(serialized.data)


class DomainClaimView(views.APIView):
    """
    A view to handle domain claims by hosting providers.
    This view ensures that only authenticated users who manage
    a hosting provider can claim a domain.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DomainClaimSerializer

    @swagger_auto_schema(tags=["Domain Claim"])
    def post(self, request, format=None):
        domain = request.data.get("domain")

        provider_id = request.data.get("provider")

        provider = Hostingprovider.objects.get(id=provider_id)

        # try to claim the domain, and raise the exception if not
        result = GreenDomain.claim_via_carbon_txt(domain, provider)

        # our serializer serves the 'claimed' result if we have
        # GreenDomain entry, otherwise 'unclaimed'
        if not result:
            # for historical reasons, the domain is listed as url in
            # the GreenDomain model
            serialized = DomainClaimSerializer(GreenDomain(url=domain))
        else:
            serialized = DomainClaimSerializer(result)

        return Response(serialized.data)
