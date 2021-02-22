import logging


from django.shortcuts import get_object_or_404
from rest_framework import mixins, pagination, parsers, request, response, viewsets
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_csv import renderers as drf_csv_rndr  # noqa
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema  # noqa

from ..models import GreencheckASN
from ..serializers import GreenDomainSerializer, GreenASNSerializer
from .permissions import BelongsToHostingProvider

logger = logging.getLogger(__name__)

ASN_API_LIST_DESCRIPTION = """
    List the AS Networks associated with this provider.

    Returns a list of AS Networks registered with the provider.
"""  # noqa
ASN_API_CREATE_DESCRIPTION = """
    Register a new AS Networks for the hosting provider associated with this user.

    Once an ASN is registered, it can take a short while before checks against the new IP
    range show as green.
"""  # noqa
ASN_API_DESTROY_DESCRIPTION = """
    Removes the association of the AS Network with the corresponding id from this
    hosting provider.

    As with POSTing a new AS Network, there can be a delay until the change propogates.

"""
ASN_API_RETRIEVE_DESCRIPTION = """
    Fetch the AS Network for the corresponding id provided.
"""


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_description=ASN_API_LIST_DESCRIPTION, tags=["AS Network"]
    ),
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        operation_description=ASN_API_CREATE_DESCRIPTION, tags=["AS Network"]
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_description=ASN_API_RETRIEVE_DESCRIPTION, tags=["AS Network"]
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_description=ASN_API_DESTROY_DESCRIPTION, tags=["AS Network"]
    ),
)
class ASNViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    This viewset automatically provides `list` and `retrieve` actions.
    We don't want ASNs to be editable once created, as they're often linked
    to an request to approve it.
    So, we expose 'create', 'destroy' and 'list' methods.
    Similarly, 'delete' does not delete a range, but instead it marks the IP range
    as inactive.
    """

    serializer_class = GreenASNSerializer
    queryset = GreencheckASN.objects.all()

    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [BelongsToHostingProvider]

    def filter_queryset(self, queryset):
        """
        Because our viewset takes care of pagination and the rest
        all we change is what is returned when we filter the queryset
        for a given user.

        http://www.cdrf.co/3.9/rest_framework.viewsets/ModelViewSet.html#list
        """

        user = self.request.user

        if user is not None:
            provider = self.request.user.hostingprovider

            if provider is not None:
                return provider.greencheckasn_set.filter(active=True)

        return []

    def perform_destroy(self, instance):
        """
        Overriding this one function means that the rest of
        our destroy method works as expected.
        """
        instance.active = False
        instance.save()

