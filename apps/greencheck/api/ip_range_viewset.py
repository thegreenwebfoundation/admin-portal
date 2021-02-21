import logging


from django.shortcuts import get_object_or_404
from rest_framework import mixins, pagination, parsers, request, response, viewsets
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_csv import renderers as drf_csv_rndr  # noqa
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema  # noqa

from ..models import GreencheckIp, GreenDomain
from ..serializers import (
    GreenDomainBatchSerializer,
    GreenDomainSerializer,
    GreenIPRangeSerializer,
)

logger = logging.getLogger(__name__)

IP_RANGE_API_LIST_DESCRIPTION = """
    LISTNG DESCRIPTION GOES HERE
"""
IP_RANGE_API_CREATE_DESCRIPTION = """
    CREATE DESCRIPTION GOES HERE
"""
IP_RANGE_API_DESTROY_DESCRIPTION = """
    DESTROY DESCRIPTION GOES HERE.

"""
IP_RANGE_API_RETRIEVE_DESCRIPTION = """
    RETRIEVE DESCRPTION GOES HERE
"""


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(operation_description=IP_RANGE_API_LIST_DESCRIPTION),
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        operation_description=IP_RANGE_API_CREATE_DESCRIPTION
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_description=IP_RANGE_API_RETRIEVE_DESCRIPTION
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_description=IP_RANGE_API_DESTROY_DESCRIPTION
    ),
)
class IPRangeViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    This viewset automatically provides `list` and `retrieve` actions.
    We don't want ip-ranges to be editable once created, as they're often linked
    to an request to approve a set range.
    So, we exposes a 'create', 'destroy' and 'list' methods.
    Similarly, 'delete' does not delete a range, but instead it marks the IP range
    as inactive.
    """

    serializer_class = GreenIPRangeSerializer
    queryset = GreencheckIp.objects.all()

    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

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
                return provider.greencheckip_set.filter(active=True)

        return []

    def perform_destroy(self, instance):
        """
        Overriding this one function means that the rest of
        our destroy method works as expected.
        """

        # check if this user is authorised to modify this ip range

        instance.active = False
        instance.save()

