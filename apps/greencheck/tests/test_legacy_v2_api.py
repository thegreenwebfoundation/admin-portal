# import webbrowser
import json

from django.urls import reverse

from ..models import GreencheckIp
from ...accounts import models as ac_models
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
