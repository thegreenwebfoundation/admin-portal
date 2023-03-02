import logging

from rest_framework import permissions, views
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from ..serializers import CarbonTxtSerializer
from ..carbon_txt import CarbonTxtParser

logger = logging.getLogger(__name__)
parser = CarbonTxtParser()


class CarbonTxtAPI(views.APIView):
    """
    A view for providing a validator service for carbon.txt files
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = CarbonTxtSerializer

    @swagger_auto_schema(tags=["Carbon.txt"])
    def put(self, request):
        """
        Return the information we have for the providers mentioned in
        a given carbon.txt file
        """

        carbon_txt_url = request.data["url"]
        carbon_txt_content = request.data["carbon_txt"]

        if carbon_txt_content:
            parsed = parser.parse(carbon_txt_url, carbon_txt_content)
            serialized = CarbonTxtSerializer(parsed)
            return Response(serialized.data)

        parsed = parser.parse_from_url(carbon_txt_url)
        serialized = CarbonTxtSerializer(parsed)
        return Response(serialized.data)
