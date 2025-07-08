import ipaddress
import json
from typing import List

import pytest
from django.utils import text
from django.shortcuts import reverse
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from ..api.legacy_views import fetch_providers_for_country
from ..models import GreencheckIp
from ...accounts import models as ac_models

from apps.accounts.models import DatacenterCertificate
from . import setup_domains

THREE_MONTHS_BACK = timezone.now() + relativedelta(weeks=-12)
YEAR_FROM_NOW = timezone.now() + relativedelta(years=1)


@pytest.fixture
def green_dc_certificate(datacenter):
    return DatacenterCertificate(
        energyprovider="Some Energy Co.",
        mainenergy_type="mixed",
        url="https://link.to.company/certificate.pdf",
        valid_from=THREE_MONTHS_BACK,
        valid_to=YEAR_FROM_NOW,
        datacenter=datacenter,
    )


def named_hosting_provider(name: str) -> ac_models.Hostingprovider:
    """
    Return a hosting provider with the given name
    """
    return ac_models.Hostingprovider(
        archived=False,
        country="US",
        customer=False,
        icon="",
        iconurl="",
        model="groeneenergie",
        name=name,
        partner="",
        is_listed=True,
        website=f"http://{text.slugify(name)}.com",
    )


@pytest.fixture
def hosting_provider_a():
    return named_hosting_provider("aaardvark solutions")


@pytest.fixture
def hosting_provider_z():
    return named_hosting_provider("zebra tech")


def add_green_ip_to(
    hosting_provider: ac_models.Hostingprovider, ip_list: List[ipaddress.ip_address]
) -> GreencheckIp:
    """
    Set a green ip for the given hosting provider, and associate it with it.
    """
    hosting_provider.save()
    return GreencheckIp.objects.create(
        active=True,
        ip_start=ip_list[0],
        ip_end=ip_list[1],
        hostingprovider=hosting_provider,
    )


class TestGreenWebDirectoryListing:
    def test_legacy_directory_ordering(
        self, db, hosting_provider_a, hosting_provider_z, client
    ):
        """
        Inside a given country are we listing providers alphabetically?
        """
        add_green_ip_to(hosting_provider_a, ["172.217.168.238", "172.217.168.238"])
        add_green_ip_to(hosting_provider_z, ["172.217.168.239", "172.217.168.239"])

        setup_domains(
            [hosting_provider_a.website],
            hosting_provider_a,
            hosting_provider_a.greencheckip_set.first(),
        )
        setup_domains(
            [hosting_provider_z.website],
            hosting_provider_z,
            hosting_provider_z.greencheckip_set.first(),
        )

        providers = fetch_providers_for_country("US")

        #  is the first provider the one we expect to see
        assert providers[0]["naam"] == hosting_provider_a.name

    def test_legacy_directory_partner_priority(
        self, db, hosting_provider_a, hosting_provider_z
    ):
        """
        Inside a given country, with certified providers, are they listed first?
        """
        add_green_ip_to(hosting_provider_a, ["172.217.168.238", "172.217.168.238"])
        add_green_ip_to(hosting_provider_z, ["172.217.168.239", "172.217.168.239"])

        # setup up A
        setup_domains(
            [hosting_provider_a.website],
            hosting_provider_a,
            hosting_provider_a.greencheckip_set.first(),
        )
        # setup up Z
        setup_domains(
            [hosting_provider_z.website],
            hosting_provider_z,
            hosting_provider_z.greencheckip_set.first(),
        )
        hosting_provider_z.partner = "Certified Provider"
        hosting_provider_z.save()

        providers = fetch_providers_for_country("US")

        #  is the first provider the one we expect to see
        assert providers[0]["naam"] == hosting_provider_z.name


class TestGreenWebDirectoryDetail:
    """
    Check that a directory detail API call exposes
    information necessary for listing in the directory
    """

    def test_directory_provider(self, db, hosting_provider_a, client):
        hosting_provider_a.save()
        url_path = reverse("legacy-directory-detail", args=[hosting_provider_a.id])

        resp = client.get(url_path)

        payload = json.loads(resp.content)
        provider = payload[0]

        for key in [
            "id",
            "naam",
            "website",
            "countrydomain",
            "model",
            "certurl",
            "valid_from",
            "valid_to",
            "mainenergytype",
            "energyprovider",
            "partner",
            "datacenters",
        ]:
            assert key in provider

    @pytest.mark.parametrize("website_link", ["https://my-domain.com", "http://my-domain.com", "my-domain.com"])
    def test_directory_provider_protocol_stripped(self, db, hosting_provider_a, client, website_link):
        """
        Test that urls are listed in the directory without the protocol,
        so "https://my-domain.com", ends up as "my-domain.com".
        This is avoid links breaking when rendered by old jQuery code
        """

        hosting_provider_a.save()
        hosting_provider_a.website = website_link
        url_path = reverse("legacy-directory-detail", args=[hosting_provider_a.id])

        resp = client.get(url_path)

        payload = json.loads(resp.content)
        provider = payload[0]

        assert "http" not in provider["website"]


    def test_directory_provider_with_datacentre(
        self,
        db,
        hosting_provider_a,
        sample_hoster_user,
        datacenter,
        green_dc_certificate,
        client,
    ):
        """
        Are we showing the datacentres in the data structure too?
        """
        # fetch with regular client

        hosting_provider_a.save()
        sample_hoster_user.save()

        datacenter.user_id = sample_hoster_user.id
        datacenter.save()
        hosting_provider_a.datacenter.add(datacenter)
        hosting_provider_a.save()
        green_dc_certificate.datacenter = datacenter
        green_dc_certificate.save()
        datacenter.save()

        url_path = reverse("legacy-directory-detail", args=[hosting_provider_a.id])

        resp = client.get(url_path)

        payload = json.loads(resp.content)
        provider = payload[0]

        assert len(provider["datacenters"]) == 1
        dc = provider["datacenters"][0]

        for key in [
            "city",
            "country",
            "countrydomain",
            "id",
            "naam",
            "pue",
            "website",
        ]:
            assert key in dc

    def test_directory_provider_with_certificates(
        self,
        db,
        hosting_provider_a,
        sample_hoster_user,
        datacenter,
        green_dc_certificate,
        client,
    ):
        """
        Are we showing the certificates we have for the
        datacentres as well?
        """
        hosting_provider_a.save()
        sample_hoster_user.save()

        datacenter.user_id = sample_hoster_user.id
        datacenter.save()
        hosting_provider_a.datacenter.add(datacenter)
        hosting_provider_a.save()
        green_dc_certificate.datacenter = datacenter
        green_dc_certificate.save()
        datacenter.save()

        url_path = reverse("legacy-directory-detail", args=[hosting_provider_a.id])

        resp = client.get(url_path)

        payload = json.loads(resp.content)
        provider = payload[0]

        assert len(provider["datacenters"]) == 1
        dc = provider["datacenters"][0]

        certs = dc["certificates"]
        assert len(certs) == 1

        cert = certs[0]

        for key in [
            "cert_valid_from",
            "cert_valid_to",
            "cert_url",
        ]:
            assert key in cert

    def test_directory_provider_raises_against_undefined_provider(
        self, db, hosting_provider_a, client
    ):
        """
        Make sure that when client side code tries to request a provider
        with the id of 'undefined' we serve an appropriate error
        40x response, rather than raising an helpful 500 server error
        """
        # Given: a valid hosting provider, but an invalid id of 'undefined' from
        # client side code making requests
        hosting_provider_a.save()
        url_path = reverse("legacy-directory-detail", args=["undefined"])

        # When: I send an API reqeest
        resp = client.get(url_path)

        # Then: I should receive a helpful API error response
        assert resp.status_code == 400

        # And: with hints about how to fix my request
        error_detail = resp.data["detail"]
        error_message = str(error_detail)

        assert error_detail.code == "parse_error"
        assert "You need to send a valid numeric ID" in error_message
        assert "Received ID was: 'undefined'" in error_message
