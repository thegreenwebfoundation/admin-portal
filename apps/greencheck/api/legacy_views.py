import json
from rest_framework.permissions import AllowAny
from apps.accounts.models import Hostingprovider
from rest_framework import response
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework_jsonp.renderers import JSONPRenderer

from ..models import Greencheck


def augmented_greencheck(check):
    """
    Return an augmented greencheck with necessary information to
    """
    if check.green == "yes":
        hosting_provider = Hostingprovider.objects.get(pk=check.hostingprovider)
        return {
            "date": str(check.date),
            "url": check.url,
            "hostingProviderId": check.hostingprovider,
            "hostingProviderUrl": hosting_provider.website,
            "hostingProviderName": hosting_provider.name,
            "green": True,
        }
    else:
        return
        {
            "date": str(check.date),
            "url": check.url,
            "hostingProviderId": False,
            "hostingProviderUrl": False,
            "hostingProviderName": False,
            "green": False,
        }


@api_view()
@permission_classes([AllowAny])
@renderer_classes([JSONPRenderer])
def latest_greenchecks(request):
    checks = Greencheck.objects.all()[:10]
    payload = []
    for check in checks:
        updated_check = augmented_greencheck(check)
        payload.append(updated_check)

    json_payload = json.dumps(payload)
    return response.Response(json_payload)
