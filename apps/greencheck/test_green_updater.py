import pytest

from datetime import datetime
from apps.greencheck.models import (
    GreenPresenting,
    Greencheck,
    TopUrl,
    Hostingprovider,
    GreencheckIp,
)
from apps.greencheck.management.commands.update_top_url_list import TopUrlUpdater

tu_updater = TopUrlUpdater()


@pytest.fixture
def hosting_provider():

    return Hostingprovider(
        archived=False,
        country="US",
        customer=False,
        icon="",
        iconurl="",
        model="groeneenergie",
        name="Google",
        partner="",
        showonwebsite=True,
        website="http://google.com",
    )


@pytest.fixture
def greencheck(hosting_provider, green_ip):
    now = datetime.now()
    hosting_provider.save()
    return Greencheck(
        hostingprovider=hosting_provider.id,
        date=datetime(now.year, now.month, now.day, now.hour, now.second),
        green="yes",
        greencheck_ip=green_ip.id,
        ip=12345,
        tld="com",
        type="as",
        url="google.com",
    )


@pytest.fixture
def top_url():
    return TopUrl(url="google.com")


class TestUpdateList:
    def test_update_green_list(self, db, greencheck, top_url):

        assert GreenPresenting.objects.count() == 0

        # set up fixture
        top_url.save()
        greencheck.save()

        top_urls = TopUrl.objects.all()
        tu_updater.update_green_domains(top_urls)

        # check we have the value
        gp_google = GreenPresenting.objects.filter(url="google.com").first()
        assert gp_google.url == "google.com"

        assert gp_google.modified == greencheck.date

    def test_update_green_list_with_existing_green_domain(
        self, db, greencheck, top_url
    ):

        # set up fixture
        top_url.save()
        greencheck.save()
        hostingprovider = Hostingprovider.objects.get(pk=greencheck.hostingprovider)

        gp = GreenPresenting(
            green=True,
            hosted_by_id=greencheck.hostingprovider,
            hosted_by=hostingprovider,
            hosted_by_website=hostingprovider.website,
            url=greencheck.url,
            partner=hostingprovider.partner,
            modified=greencheck.date,
        )
        gp.save()

        top_urls = TopUrl.objects.all()
        tu_updater.update_green_domains(top_urls)

        # check we have the value
        gp_google = GreenPresenting.objects.filter(url="google.com").first()
        assert gp_google.url == "google.com"

        assert gp_google.modified == greencheck.date
        assert GreenPresenting.objects.filter(url="google.com").count() == 1

