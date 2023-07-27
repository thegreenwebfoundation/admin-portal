import pytest
import requests
import time
from django.urls import reverse

from drf_api_logger.models import APILogsModel


@pytest.mark.django_db
def test_api_requests_are_logged(live_server):
    """
    Check that API requests are logged. We need a live server, because the 
    api request logger runs in a separata thread that is spun up only when 
    the live server is running.
    """

    # when: a request has been made to  our high traffic endpoint use for most greenchecks
    res = requests.get(f"{live_server.url}{reverse('asn-list')}")
    
    # Note: django api request logger works by logging API requests outside the normal 
    # request lifecycle. By default, it writes to the db every 10 seconds, but the 
    # minimum we can set this to is 1 seconds in testing.DRF_LOGGER_INTERVAL

    # and: our api request logging internal has elapsed
    time.sleep(1)

    # then we should see one request logged
    assert APILogsModel.objects.count() is 1


@pytest.mark.django_db
def test_high_traffic_api_requests_are_not_logged(live_server):
    """
    Check we do not try to log requests on endpoints where it does not make sense to do so.
    Some receive so much traffic that it would be impractical, for example.
    """

    # given: a request has been made to  our high traffic endpoint use for most greenchecks
    requests.get(f"{live_server.url}{reverse('green-domain-detail', args=['example.com'])}")

    # and: a request our endpoint for generating images - also sees a lot use
    requests.get(f"{live_server.url}{reverse('legacy-greencheck-image', args=['example.com'])}")
    
    # and: our logged has had time to log the requests
    time.sleep(1)
    
    # then: we should see no logged requests
    assert APILogsModel.objects.count() is 0

