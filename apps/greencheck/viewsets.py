import logging

from rest_framework import viewsets
from .serializers import GreenIPRangeSerializer
from .models import GreencheckIp, Hostingprovider
from rest_framework import response
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated


logger = logging.getLogger(__name__)


class IPRangeViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list` and `retrieve` actions.
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
        instance.active = False
        instance.save()

