from datetime import datetime

import pytest

from ...accounts import models as ac_models
from .. import choices as gc_choices
from .. import factories as gc_factories
from .. import models as gc_models
from ..management.commands import update_top_url_list

tu_updater = update_top_url_list.TopUrlUpdater()


@pytest.fixture
def hosting_provider():

    return ac_models.Hostingprovider(
        archived=False,
        country="US",
        customer=False,
        icon="",
        iconurl="",
        model="groeneenergie",
        name="Google",
        partner="",
        is_listed=True,
        website="http://google.com",
    )


@pytest.fixture
def greencheck(hosting_provider, green_ip):

    now = datetime.now()
    hosting_provider.save()

    return gc_factories.GreencheckFactory.create(
        date=datetime(now.year, now.month, now.day, now.hour, now.second),
        url="google.com",
        tld="com",
        green=gc_choices.BoolChoice.YES,
        hostingprovider=hosting_provider.id,
        greencheck_ip=green_ip.id,
        type=gc_choices.GreenlistChoice.ASN,
    )


@pytest.fixture
def top_url():
    return gc_models.TopUrl(url="google.com")


class TestUpdateList:
    def test_update_green_list(self, db, greencheck, top_url):

        assert gc_models.GreenDomain.objects.count() == 0

        # set up fixture
        top_url.save()
        greencheck.save()

        top_urls = gc_models.TopUrl.objects.all()
        tu_updater.update_green_domains(top_urls)

        # check we have the value
        gp_google = gc_models.GreenDomain.objects.filter(url="google.com").first()
        assert gp_google.url == "google.com"

        assert gp_google.modified == greencheck.date

    def test_update_green_list_with_existing_green_domain(
        self, db, greencheck, top_url
    ):

        # set up fixture
        top_url.save()
        greencheck.save()
        hostingprovider = ac_models.Hostingprovider.objects.get(
            pk=greencheck.hostingprovider
        )

        gp = gc_models.GreenDomain(
            green=True,
            hosted_by_id=greencheck.hostingprovider,
            hosted_by=hostingprovider,
            hosted_by_website=hostingprovider.website,
            url=greencheck.url,
            partner=hostingprovider.partner,
            modified=greencheck.date,
        )
        gp.save()

        top_urls = gc_models.TopUrl.objects.all()
        tu_updater.update_green_domains(top_urls)

        # check we have the value
        gp_google = gc_models.GreenDomain.objects.filter(url="google.com").first()
        assert gp_google.url == "google.com"

        assert gp_google.modified == greencheck.date
        assert gc_models.GreenDomain.objects.filter(url="google.com").count() == 1
