import ipaddress
from typing import List

import pytest
from django.utils import text

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


class TestGreenWebDirectory:
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
        self, db, hosting_provider_a, hosting_provider_z, client
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

