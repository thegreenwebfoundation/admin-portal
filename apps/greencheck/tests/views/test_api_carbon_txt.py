import logging
import pytest
import pathlib

from django.urls import reverse
from rest_framework.test import APIRequestFactory

from ... import api


pytestmark = pytest.mark.django_db

logger = logging.getLogger(__name__)

rf = APIRequestFactory()


@pytest.fixture
def carbon_txt_string():
    pth = pathlib.Path(__file__)

    carbon_txt_path = pth.parent.parent / "carbon-txt-samples" / "carbon-txt-test.toml"

    carbon_txt_string = None
    with open(carbon_txt_path) as carb_file:
        carbon_txt_string = carb_file.read()

    return carbon_txt_string


class TestCarbonTxtAPI:
    def test_carbon_txt_url_and_content(
        self,
        db,
        carbon_txt_string,
        hosting_provider_factory,
        supporting_evidence_factory,
        green_domain_factory,
    ):
        """Check our seriliasation works"""
        provider = hosting_provider_factory.create(
            name="www.hillbob.de", website="https://www.hillbob.de"
        )
        supporting_evidence_factory.create(hostingprovider=provider)

        # create our upstream providers
        systen_upstream = hosting_provider_factory.create(
            name="sys-ten.com", website="https://sys-ten.com"
        )
        supporting_evidence_factory.create(
            hostingprovider=systen_upstream,
            url="https://www.sys-ten.de/en/about-us/our-data-centers/",
        )

        cdn_upstream = hosting_provider_factory.create(
            name="cdn.com", website="https://cdn.com"
        )
        supporting_evidence_factory.create(
            hostingprovider=cdn_upstream,
            url="https://cdn.com/company/corporate-responsibility/sustainability",
        )

        # create our domains we use to look up each provider
        green_domain_factory.create(hosted_by=provider, url="www.hillbob.de")
        green_domain_factory.create(hosted_by=systen_upstream, url="sys-ten.com")
        green_domain_factory.create(hosted_by=cdn_upstream, url="cdn.com")

        url_path = reverse("carbon-txt-parse")
        request = rf.put(
            url_path,
            {
                "url": "https://www.hillbob.de/carbon.txt",
                "carbon_txt": carbon_txt_string,
            },
        )

        # PUT end point for testing carbontxt
        view_func = api.views.CarbonTxtAPI.as_view()

        response = view_func(request)

        assert response.status_code == 200
