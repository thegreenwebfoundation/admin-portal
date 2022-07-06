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
        for _ in range(3):
            hosting_provider_factory.create(partner="Partner", showonwebsite=True)

        for _ in range(3):
            hosting_provider_factory.create(partner="", showonwebsite=True)

        res = legacy_views.fetch_providers_for_country("US")

        # Are the first three entries the partners and also the same order?
        partners_in_response = res[:3]
        reg_providers_in_response = res[3:]

        partners_in_db = (
            ac_models.Hostingprovider.objects.filter(partner="Partner")
            .order_by("name")
            .values("name", "partner")
        )

        reg_providers_in_db = (
            ac_models.Hostingprovider.objects.filter(partner="")
            .order_by("name")
            .values("name", "partner")
        )

        # Are the first entries partners, and also in ascending order?
        for index in range(3):
            res_name = partners_in_response[index]["naam"]
            res_partner = partners_in_response[index]["partner"]

            db_name = partners_in_db[index]["name"]
            db_partner = partners_in_db[index]["partner"]

            assert res_name == db_name
            assert res_partner == db_partner

        # Are the second entries not partners, but also in ascending order?
        for index in range(3):
            res_name = reg_providers_in_response[index]["naam"]
            res_partner = reg_providers_in_response[index]["partner"]

            db_name = reg_providers_in_db[index]["name"]
            db_partner = reg_providers_in_db[index]["partner"]

            assert res_name == db_name
            assert res_partner == db_partner

