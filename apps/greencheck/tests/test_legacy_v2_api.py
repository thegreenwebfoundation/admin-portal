# import webbrowser
import json

from django.urls import reverse

from ..models import GreencheckIp
from ...accounts import models as ac_models
from ...greencheck.api import legacy_views
from . import setup_domains


class TestGreencheckMultiView:
    def test_multi_check(
        self,
        db,
        client,
        hosting_provider_with_sample_user: ac_models.Hostingprovider,
        green_ip: GreencheckIp,
    ):

        #
        # add our green domains
        setup_domains(
            ["www.facebook.com", "twitter.com", "www.youtube.com"],
            hosting_provider_with_sample_user,
            green_ip,
        )

        # fmt: off
        urls_string = '["www.acethinker.com","download.acethinker.com","www.avangatenetwork.com","www.facebook.com","twitter.com","www.youtube.com","acethinker.com"]' # noqa
        # urls_string = '[%22docs.google.com%22,%22accounts.google.com%22,%22www.google.com%22,%22myaccount.google.com%22,%22policies.google.com%22]' # noqa
        # fmt: on

        # urls = json.loads(parse.unquote(urls_string))
        urls = json.loads(urls_string)

        response = client.get(reverse("legacy-greencheck-multi", args=[urls_string]))
        returned_domains = response.data.keys()
        for url in urls:
            assert url in returned_domains

        assert response.status_code == 200

    def test_multi_check_with_null_value(
        self,
        db,
        client,
        hosting_provider_with_sample_user: ac_models.Hostingprovider,
        green_ip: GreencheckIp,
    ):

        urls_string = "null"

        response = client.get(reverse("legacy-greencheck-multi", args=[urls_string]))
        assert response.status_code == 200


class TestDirectoryListingView:
    """
    Does our legacy directory endpoint list providers in the
    correct order?
    """

    def test_list_directory_order_grouped(self, db, hosting_provider_factory):

        # given: 9 providers, out of which 3 are partners
        partners = []
        nonpartners = []
        # For legacy reasons, the non-partner providers can be represented either:
        # - with empty string
        # - or None.
        # The factory fixture creates non-partner and partner providers in a way
        # that avoids those objects to be already sorted, to create a more
        # realistic testing scenario.
        for _ in range(3):
            p1 = hosting_provider_factory.create(partner="", is_listed=True)
            p2 = hosting_provider_factory.create(partner="Partner", is_listed=True)
            p3 = hosting_provider_factory.create(partner=None, is_listed=True)
            partners.append(p2)
            nonpartners.extend([p1, p3])

        sorted_partners = sorted(partners, key=lambda x: x.name)
        sorted_nonpartners = sorted(nonpartners, key=lambda x: x.name)

        # when: requesting all providers
        res = legacy_views.fetch_providers_for_country("US")

        # then: first 3 items in the response are partners, sorted alphabetically by name
        for index in range(3):
            assert res[index]["naam"] == sorted_partners[index].name
            assert res[index]["partner"] == sorted_partners[index].partner

        # then: remaining items are sorted alphabetically by name
        for index in range(6):
            assert res[index + 3]["naam"] == sorted_nonpartners[index].name
            assert res[index + 3]["partner"] == sorted_nonpartners[index].partner
