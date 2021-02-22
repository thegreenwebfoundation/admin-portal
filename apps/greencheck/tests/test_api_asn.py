import logging
import pytest

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from apps.greencheck.models import GreencheckASN, Hostingprovider
from apps.greencheck.viewsets import ASNViewSet

User = get_user_model()

pytestmark = pytest.mark.django_db

logger = logging.getLogger(__name__)

rf = APIRequestFactory()


class TestASNViewSetList:
    def test_get_asn_empty(self, hosting_provider_with_sample_user: Hostingprovider):
        """
        Exercise the simplest happy path - we return an empty list for a hosting
        provider with no ASNS registered.
        """

        rf = APIRequestFactory()
        url_path = reverse("asn-list")
        request = rf.get(url_path)
        request.user = hosting_provider_with_sample_user.user_set.first()

        # GET end point for IP Ranges
        view = ASNViewSet.as_view({"get": "list"})

        response = view(request)

        # check contents
        assert response.status_code == 200
        assert len(response.data) == 0

    def test_get_asn_list(
        self,
        hosting_provider_with_sample_user: Hostingprovider,
        green_asn: GreencheckASN,
    ):
        """
        Check that we can list the ASNs for given provider
        """
        green_asn.save()

        rf = APIRequestFactory()
        url_path = reverse("asn-list")
        request = rf.get(url_path)
        request.user = hosting_provider_with_sample_user.user_set.first()

        # GET end point for IP Ranges
        view = ASNViewSet.as_view({"get": "list"})

        response = view(request)

        # check contents
        assert response.status_code == 200
        assert len(response.data) == 1

        first_asn_data = response.data[0]
        assert first_asn_data["id"] == green_asn.id
        assert first_asn_data["asn"] == green_asn.asn

    def test_get_asn_retrieve(
        self,
        hosting_provider_with_sample_user: Hostingprovider,
        green_asn: GreencheckASN,
    ):
        """
        Check that we can fetch an individual ASN for the provider
        """
        green_asn.save()

        rf = APIRequestFactory()
        url_path = reverse("asn-detail", kwargs={"pk": green_asn.id})
        request = rf.get(url_path)
        request.user = hosting_provider_with_sample_user.user_set.first()

        # GET end point for IP Ranges
        view = ASNViewSet.as_view({"get": "retrieve"})

        response = view(request, pk=green_asn.id)

        # check contents
        assert response.status_code == 200

        response.data["asn"] == green_asn.asn
        response.data["id"] == green_asn.id
        response.data["hostingprovider"] == green_asn.hostingprovider.id

    def test_get_asn_create(
        self, hosting_provider_with_sample_user: Hostingprovider,
    ):
        """
        Can we create an new ASN over the API, for our hosting provider?
        """
        rf = APIRequestFactory()
        url_path = reverse("asn-list")
        user = hosting_provider_with_sample_user.user_set.first()
        data = {
            "asn": 12345,
            "hostingprovider": hosting_provider_with_sample_user.id,
        }
        request = rf.post(url_path, data)
        request.user = user

        # GET end point for IP Ranges
        view = ASNViewSet.as_view({"post": "create"})

        response = view(request)

        # check contents
        assert response.status_code == 201
        response.data["asn"] == 12345
        response.data["hostingprovider"] == hosting_provider_with_sample_user.id

        green_asn, *_ = GreencheckASN.objects.filter(asn=12345)
        response.data["id"] == green_asn.id

    # no duplicates

    def test_get_asn_delete(
        self,
        hosting_provider_with_sample_user: Hostingprovider,
        green_asn: GreencheckASN,
    ):
        """
        Can we delete an ASN via the API, marking it as 'inactive' in our database?
        """

        green_asn.save()

        rf = APIRequestFactory()
        url_path = reverse("asn-detail", kwargs={"pk": green_asn.id})
        user = hosting_provider_with_sample_user.user_set.first()
        request = rf.delete(url_path)
        request.user = user

        # GET end point for IP Ranges
        view = ASNViewSet.as_view({"delete": "destroy"})

        response = view(request, pk=green_asn.id)

        # check contents
        assert response.status_code == 204
        assert GreencheckASN.objects.filter(asn=12345).count() == 1

        fetched_green_asn = GreencheckASN.objects.filter(asn=12345).first()
        assert fetched_green_asn.active == False
