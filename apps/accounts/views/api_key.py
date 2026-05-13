from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import APIKey
from ..permissions import HasGWFSharedSecret

class APIKeyIntrospectionView(APIView):
    """
    Internal: called by other services to validate a key.
    Protected by a shared secret — not user-facing.
    """
    permission_classes = [HasGWFSharedSecret]

    def post(self, request):
        raw_key = request.data.get("token", "")

        try:
            key = APIKey.objects.get_from_key(raw_key)
            return Response({
                "active": True,
                "user_id": key.user_id,
                "username": key.user.username,
                "expiry_date": key.expiry_date,
                "prefix": key.prefix,
            })
        except APIKey.DoesNotExist:
            return Response({"active": False})

