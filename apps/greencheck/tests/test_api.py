import csv
import io
import logging

import pytest

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.authtoken import models, views
from rest_framework.test import APIRequestFactory

from . import greencheck_sitecheck
from ..legacy_workers import LegacySiteCheckLogger
from ..models import GreencheckIp, Hostingprovider
from ..viewsets import GreenDomainViewset

User = get_user_model()

pytestmark = pytest.mark.django_db

logger = logging.getLogger(__name__)

rf = APIRequestFactory()


def setup_domains(domains, hosting_provider, green_ip):
    sitecheck_logger = LegacySiteCheckLogger()

    for domain in domains:
        sitecheck = greencheck_sitecheck(domain, hosting_provider, green_ip)
        sitecheck_logger.update_green_domain_caches(sitecheck, hosting_provider)


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

        assert response.status_code == 200
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
        hosting_provider_with_sample_user: Hostingprovider,
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

        setup_domains(domains, hosting_provider_with_sample_user, green_ip)

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
        hosting_provider_with_sample_user: Hostingprovider,
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

        setup_domains(green_domains, hosting_provider_with_sample_user, green_ip)

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
        hosting_provider_with_sample_user: Hostingprovider,
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

        setup_domains(green_domains, hosting_provider_with_sample_user, green_ip)

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
