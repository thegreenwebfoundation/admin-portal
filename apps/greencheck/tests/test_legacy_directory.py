import ipaddress
import json
from typing import List

import pytest
from django.utils import text
from django.shortcuts import reverse

from ..api.legacy_views import fetch_providers_for_country
from ..models import GreencheckIp, Hostingprovider
from . import setup_domains


def named_hosting_provider(name: str) -> Hostingprovider:
    """
    Return a hosting provider with the given name
    """
    return Hostingprovider(
        archived=False,
        country="US",
        customer=False,
        icon="",
        iconurl="",
        model="groeneenergie",
        name=name,
        partner="",
        showonwebsite=True,
        website=f"http://{text.slugify(name)}.com",
    )


@pytest.fixture
def hosting_provider_a():
    return named_hosting_provider("aaardvark solutions")


@pytest.fixture
def hosting_provider_z():
    return named_hosting_provider("zebra tech")


def add_green_ip_to(
    hosting_provider: Hostingprovider, ip_list: List[ipaddress.ip_address]
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

    def test_directory_provider_with_datacentre(
        self, db, hosting_provider_a, sample_hoster_user, datacenter, client
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
        datacenter.save()

        url_path = reverse("legacy-directory-detail", args=[hosting_provider_a.id])

        resp = client.get(url_path)

        payload = json.loads(resp.content)

        # legacy payload
        # [
        #     {
        #         "id": "380",
        #         "naam": "Netcetera",
        #         "website": "http://www.website.co.uk",
        #         "countrydomain": "UK",
        #         "model": "groeneenergie",
        #         "certurl": null,
        #         "valid_from": null,
        #         "valid_to": null,
        #         "mainenergytype": null,
        #         "energyprovider": null,
        #         "partner": "",
        #         "datacenters": [
        #             {
        #                 "id": "28",
        #                 "naam": "Website Dataport",
        #                 "website": "http://www.website.co.uk",
        #                 "countrydomain": "UK",
        #                 "model": "groeneenergie",
        #                 "pue": "1.2",
        #                 "mja3": "0",
        #                 "city": "Ballasalla",
        #                 "country": "Isle of Man",
        #                 "classification": null,
        #                 "certificates": [],
        #                 "classifications": [],
        #             }
        #         ],
        #     }
        # ]

        pass

    def test_directory_provider_with_certificates(self, db, hosting_provider_a):
        """
            Are we showing the datacentres in the data structure too?
            """
        # fetch with regular client

        # [
        #     {
        #         "id": "747",
        #         "naam": "Alfahosting GmbH",
        #         "website": "www.alfahosting.de",
        #         "countrydomain": "DE",
        #         "model": "groeneenergie",
        #         "certurl": "https://alfahosting.de/downloads/Herkunftsnachweis_Strom.pdf",
        #         "valid_from": "2018-01-01",
        #         "valid_to": "2018-12-31",
        #         "mainenergytype": "mixed",
        #         "energyprovider": "envia Mitteldeutsche Energie AG",
        #         "partner": null,
        #         "datacenters": [],
        #     },
        #     {
        #         "id": "747",
        #         "naam": "Alfahosting GmbH",
        #         "website": "www.alfahosting.de",
        #         "countrydomain": "DE",
        #         "model": "groeneenergie",
        #         "certurl": "https://cdn.marketing-cloud.io/wp-content/enviatel_dcl/uploads/2020/05/28104527/200528_Urkunde_envia_TEL_HKN_2019_nicht-editierbar.pdf",
        #         "valid_from": "2019-01-01",
        #         "valid_to": "2019-12-31",
        #         "mainenergytype": "mixed",
        #         "energyprovider": "envia Mitteldeutsche Energie AG",
        #         "partner": null,
        #         "datacenters": [],
        #     },
        # ]
        pass

