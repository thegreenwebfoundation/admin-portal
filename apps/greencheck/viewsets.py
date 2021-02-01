import logging

from rest_framework import viewsets
from .serializers import GreenIPRangeSerializer
from .models import GreencheckIp, Hostingprovider
from rest_framework import response

logger = logging.getLogger(__name__)


class IPRangeViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list` and `retrieve` actions.
    """

    serializer_class = GreenIPRangeSerializer

    def list(self, request):
        """
        Show the IP ranges already registered for this user's organisation
        """

        queryset = self.get_queryset(request)
        serializer = self.serializer_class(queryset, many=True)
        return response.Response(serializer.data)

    def get_queryset(self, request=None):
        provider = request.user.hostingprovider

        if provider is not None:
            return provider.greencheckip_set.all()
        # otherwise fall back to return an empty list
        return []

    def update(self, request, *args, **kwargs):
        """
        """
        import ipdb

        ipdb.set_trace()
        return super().update(request, *args, **kwargs)
