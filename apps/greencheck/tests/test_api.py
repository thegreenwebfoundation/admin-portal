import csv
import io
import ipaddress
import logging
import pathlib

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone
from rest_framework import serializers
from rest_framework.authtoken import models, views
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APIRequestFactory, RequestsClient

from apps.greencheck.legacy_workers import LegacySiteCheckLogger, SiteCheck
from apps.greencheck.models import GreencheckIp, Hostingprovider
from apps.greencheck.viewsets import (
    GreenDomainBatchView,
    GreenDomainViewset,
    IPRangeViewSet,
)

User = get_user_model()

pytestmark = pytest.mark.django_db

logger = logging.getLogger(__name__)

rf = APIRequestFactory()


@pytest.fixture
def hosting_provider_with_user(hosting_provider, sample_hoster_user):
    hosting_provider.save()
    sample_hoster_user.hostingprovider = hosting_provider
    sample_hoster_user.save()
    return hosting_provider


def setup_domains(domains, hosting_provider, green_ip):
    sitecheck_logger = LegacySiteCheckLogger()

    for domain in domains:
        sitecheck = greencheck_sitecheck(domain, hosting_provider, green_ip)
        sitecheck_logger.update_green_domain_caches(sitecheck, hosting_provider)


def greencheck_sitecheck(
    domain, hosting_provider: Hostingprovider, green_ip: GreencheckIp
):

    return SiteCheck(
        url=domain,
        ip="192.30.252.153",
        data=True,
        green=True,
        hosting_provider_id=hosting_provider.id,
        checked_at=timezone.now(),
        match_type="ip",
        match_ip_range=green_ip.id,
        cached=True,
    )


def parse_csv_from_response(response):
    """
    Convenience function for working with CSV responses.
    Parses the CSV rows and returns a list of dicts, using the
    keys as columns
    """
    file_from_string = io.StringIO(response.content.decode("utf-8"))
    parsed_rows = []
    reader = csv.DictReader(file_from_string)

    for row in reader:
        logger.debug(row)
        parsed_rows.append(row)

    return parsed_rows


class TestUsingAuthToken:
    def test_fetching_auth_token(
        self, hosting_provider: Hostingprovider, sample_hoster_user: User,
    ):
        """
        Anyone who is able to update an organisation is able to
        generate an API token.
        """
        hosting_provider.save()
        sample_hoster_user.hostingprovider = hosting_provider
        sample_hoster_user.save()

        # set up our views, request factories and paths
        rf = APIRequestFactory()
        url_path = reverse("api-obtain-token")
        view = views.ObtainAuthToken.as_view()

        # create our request
        credentials = {"username": sample_hoster_user.username, "password": "topSekrit"}
        request = rf.post(url_path, credentials)

        response = view(request)
        token = models.Token.objects.get(user=sample_hoster_user)

        # check contents, is the token the right token?
        assert response.status_code == 200
        assert response.data["token"] == token.key


class TestIpRangeViewSetList:
    def test_get_ip_ranges_empty(
        self, hosting_provider: Hostingprovider, sample_hoster_user: User,
    ):
        """
        Exercise the simplest happy path.
        """

        hosting_provider.save()
        sample_hoster_user.hostingprovider = hosting_provider
        sample_hoster_user.save()

        rf = APIRequestFactory()
        url_path = reverse("ip-range-list")
        request = rf.get(url_path)
        request.user = sample_hoster_user

        # GET end point for IP Ranges
        view = IPRangeViewSet.as_view({"get": "list"})

        response = view(request)

        # check contents
        assert response.status_code == 200
        assert len(response.data) == 0

    def test_get_ip_ranges_for_hostingprovider_with_active_range(
        self,
        hosting_provider: Hostingprovider,
        sample_hoster_user: User,
        green_ip: GreencheckIp,
    ):

        hosting_provider.save()
        sample_hoster_user.hostingprovider = hosting_provider
        sample_hoster_user.save()

        rf = APIRequestFactory()
        url_path = reverse("ip-range-list")
        request = rf.get(url_path)
        request.user = sample_hoster_user

        # GET end point for IP Ranges
        view = IPRangeViewSet.as_view({"get": "list"})

        response = view(request)
        ip_range, *_ = response.data

        assert response.status_code == 200
        assert len(response.data) == 1

        assert ip_range["ip_start"] == green_ip.ip_start
        assert ip_range["ip_end"] == green_ip.ip_end
        assert ip_range["hostingprovider"] == green_ip.hostingprovider.id

    def test_get_ip_ranges_for_hostingprovider_with_no_active_ones(
        self,
        hosting_provider: Hostingprovider,
        sample_hoster_user: User,
        green_ip: GreencheckIp,
    ):
        hosting_provider.save()
        sample_hoster_user.hostingprovider = hosting_provider
        sample_hoster_user.save()

        green_ip.active = False
        green_ip.save()

        rf = APIRequestFactory()
        url_path = reverse("ip-range-list")
        request = rf.get(url_path)
        request.user = sample_hoster_user

        # GET end point for IP Ranges
        view = IPRangeViewSet.as_view({"get": "list"})
        response = view(request)
        assert response.status_code == 200
        assert len(response.data) == 0

    def test_get_ip_ranges_without_auth(
        self, hosting_provider: Hostingprovider, sample_hoster_user: User,
    ):
        hosting_provider.save()
        sample_hoster_user.hostingprovider = hosting_provider
        sample_hoster_user.save()

        rf = APIRequestFactory()
        url_path = reverse("ip-range-list")
        request = rf.get(url_path)

        # set up the viewset, as a views, so it knows what to do when we
        # pass in a GET request as defined a couple of lines up
        view = IPRangeViewSet.as_view({"get": "list"})

        # ipdb.set_trace()
        # has_permission = permission.has_permission(request, None)
        # import ipdb

        # ipdb.set_trace()
        response = view(request)

        # check contents
        assert response.status_code == 403
        # assert len(response.data) == 0

    def test_get_ip_range_for_user_with_no_hosting_provider(
        self, sample_hoster_user: User, rf: RequestFactory,
    ):
        sample_hoster_user.save()

        rf = APIRequestFactory()
        url_path = reverse("ip-range-list")
        request = rf.get(url_path)
        request.user = sample_hoster_user

        # GET end point for IP Ranges
        view = IPRangeViewSet.as_view({"get": "list"})
        response = view(request)

        # check contents
        assert response.status_code == 200
        assert len(response.data) == 0


class TestIpRangeViewSetRetrieve:
    """
    Can we fetch a specific IP Range object to inspect?
    """

    def test_get_ip_range_for_hostingprovider_by_id(
        self,
        hosting_provider: Hostingprovider,
        sample_hoster_user: User,
        green_ip: GreencheckIp,
    ):

        hosting_provider.save()
        sample_hoster_user.hostingprovider = hosting_provider
        sample_hoster_user.save()

        rf = APIRequestFactory()
        url_path = reverse("ip-range-detail", kwargs={"pk": green_ip.id})
        request = rf.get(url_path)
        request.user = sample_hoster_user

        # GET end point for IP Ranges
        view = IPRangeViewSet.as_view({"get": "retrieve"})

        response = view(request, pk=green_ip.id)

        assert response.status_code == 200

        assert response.data["ip_start"] == green_ip.ip_start
        assert response.data["ip_end"] == green_ip.ip_end
        assert response.data["hostingprovider"] == green_ip.hostingprovider.id


class TestIpRangeViewSetCreate:
    def test_create_new_ip_range(
        self,
        hosting_provider: Hostingprovider,
        sample_hoster_user: User,
        green_ip: GreencheckIp,
    ):

        hosting_provider.save()
        sample_hoster_user.hostingprovider = hosting_provider
        sample_hoster_user.save()
        GreencheckIp.objects.count() == 1

        rf = APIRequestFactory()
        url_path = reverse("ip-range-list")

        sample_json = {
            "hostingprovider": hosting_provider.id,
            "ip_start": "192.168.178.121",
            "ip_end": "192.168.178.129",
        }

        request = rf.post(url_path, sample_json)
        request.user = sample_hoster_user

        view = IPRangeViewSet.as_view({"post": "create"})

        response = view(request)

        assert response.status_code == 201
        GreencheckIp.objects.count() == 2

        assert response.data["ip_start"] == "192.168.178.121"
        assert response.data["ip_end"] == "192.168.178.129"
        assert response.data["hostingprovider"] == hosting_provider.id

    @pytest.mark.skip(reason="Pending. ")
    def test_skip_duplicate_ip_range(
        self,
        hosting_provider: Hostingprovider,
        sample_hoster_user: User,
        green_ip: GreencheckIp,
    ):
        """
        When a user creates an IP Range, we want to avoid the case of them
        making a duplicate. IP Range. Even if we check in the serialiser
        class, we should make sure a sensible API error message is returned
        """
        pass


class TestIpRangeViewSetDelete:
    def test_delete_existing_ip_range(
        self,
        hosting_provider: Hostingprovider,
        sample_hoster_user: User,
        green_ip: GreencheckIp,
    ):
        """
        If a user deletes an IP Range, that has been referenced when marking
        sites as green, an actual delete will mean that all those greenchecks
        are now pointing to a non-existent range.
        We do not delete with the API - we hide them.
        """

        # arrange
        hosting_provider.save()
        sample_hoster_user.hostingprovider = hosting_provider
        sample_hoster_user.save()

        # check that we have what we expect first
        assert GreencheckIp.objects.filter(active=True).count() == 1
        assert GreencheckIp.objects.count() == 1

        rf = APIRequestFactory()
        url_path = reverse("ip-range-detail", kwargs={"pk": green_ip.id})

        # act
        request = rf.delete(url_path, pk=green_ip.id)
        request.user = sample_hoster_user
        view = IPRangeViewSet.as_view({"delete": "destroy"})
        response = view(request, pk=green_ip.id)

        # assert
        assert response.status_code == 204
        assert GreencheckIp.objects.filter(active=True).count() == 0
        assert GreencheckIp.objects.filter(active=False).count() == 1
        assert GreencheckIp.objects.count() == 1


@pytest.mark.only
class TestGreenDomainViewset:
    """
    """

    def test_check_single_url(
        self,
        hosting_provider: Hostingprovider,
        sample_hoster_user: User,
        green_ip: GreencheckIp,
    ):
        """
        Check single URL, hitting.
        """

        hosting_provider.save()
        sample_hoster_user.hostingprovider = hosting_provider
        sample_hoster_user.save()
        sitecheck_logger = LegacySiteCheckLogger()

        domain = "google.com"

        sitecheck = greencheck_sitecheck(domain, hosting_provider, green_ip)

        sitecheck_logger.update_green_domain_caches(sitecheck, hosting_provider)

        rf = APIRequestFactory()
        url_path = reverse("green-domain-detail", kwargs={"url": domain})
        logger.info(f"url_path: {url_path}")

        request = rf.get(url_path)

        view = GreenDomainViewset.as_view({"get": "retrieve"})

        response = view(request, url=domain)

        assert response.status_code is 200
        assert response.data["green"] is True

    def test_check_multple_urls(
        self,
        hosting_provider: Hostingprovider,
        sample_hoster_user: User,
        green_ip: GreencheckIp,
    ):
        """
        Check multiple URLs, sent as a batch request
        """

        hosting_provider.save()
        sample_hoster_user.hostingprovider = hosting_provider
        sample_hoster_user.save()
        sitecheck_logger = LegacySiteCheckLogger()

        domains = ["google.com", "anothergreendomain.com"]

        for domain in domains:
            sitecheck = greencheck_sitecheck(domain, hosting_provider, green_ip)
            sitecheck_logger.update_green_domain_caches(sitecheck, hosting_provider)

        rf = APIRequestFactory()
        url_path = reverse("green-domain-list")
        request = rf.get(url_path, {"urls": domains})

        view = GreenDomainViewset.as_view({"get": "list"})

        response = view(request)
        assert response.status_code == 200
        logger.debug("response.data")
        logger.debug(response.data)
        assert len(response.data) == 2


class TestGreenDomaBatchView:
    def test_check_multple_urls_via_post(
        self,
        hosting_provider_with_user: Hostingprovider,
        green_ip: GreencheckIp,
        client,
    ):
        """
        Check multiple URLs, sent as a batch request
        """
        domains = ["google.com", "anothergreendomain.com"]

        fake_csv_file = io.StringIO()
        for domain in domains:
            fake_csv_file.write(f"{domain}\n")
        fake_csv_file.seek(0)

        setup_domains(domains, hosting_provider_with_user, green_ip)

        url_path = reverse("green-domain-batch")
        response = client.post(url_path, {"urls": fake_csv_file})
        returned_domains = [data.get("url") for data in response.data]

        assert response.status_code == 200
        assert len(response.data) == 2

        for domain in domains:
            assert domain in returned_domains

    @pytest.mark.only
    def test_check_green_and_grey_urls(
        self,
        hosting_provider_with_user: Hostingprovider,
        green_ip: GreencheckIp,
        client,
    ):
        green_domains = ["google.com", "anothergreendomain.com"]
        grey_domains = ["fossilfuels4ever.com"]

        fake_csv_file = io.StringIO()
        for domain in green_domains:
            fake_csv_file.write(f"{domain}\n")

        for domain in grey_domains:
            fake_csv_file.write(f"{domain}\n")

        fake_csv_file.seek(0)

        setup_domains(green_domains, hosting_provider_with_user, green_ip)

        url_path = reverse("green-domain-batch")
        response = client.post(url_path, {"urls": fake_csv_file})
        returned_domains = [data.get("url") for data in response.data]

        assert response.status_code == 200
        assert len(response.data) == 3

        domains = green_domains + grey_domains
        for domain in domains:
            assert domain in returned_domains

    @pytest.mark.only
    def test_check_green_and_grey_urls_csv(
        self,
        hosting_provider_with_user: Hostingprovider,
        green_ip: GreencheckIp,
        client,
    ):
        green_domains = ["google.com", "anothergreendomain.com"]
        grey_domains = ["fossilfuels4ever.com"]

        fake_csv_file = io.StringIO()
        for domain in green_domains:
            fake_csv_file.write(f"{domain}\n")

        for domain in grey_domains:
            fake_csv_file.write(f"{domain}\n")

        fake_csv_file.seek(0)

        setup_domains(green_domains, hosting_provider_with_user, green_ip)

        url_path = reverse("green-domain-batch")
        response = client.post(
            url_path,
            {"urls": fake_csv_file, "response_filename": "given_filename.csv"},
            HTTP_ACCEPT="text/csv",
        )

        assert response.accepted_media_type == "text/csv"
        assert response.status_code == 200

        parsed_domains = parse_csv_from_response(response)
        returned_domains = [data.get("url") for data in parsed_domains]

        assert len(returned_domains) == 3

        domains = green_domains + grey_domains
        for domain in domains:
            assert domain in returned_domains

        assert (
            response["Content-Disposition"] == "attachment; filename=given_filename.csv"
        )

