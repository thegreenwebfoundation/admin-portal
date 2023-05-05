from ..views import ProviderPortalHomeView
from ..models import ProviderRequestStatus
from conftest import ProviderRequestFactory, ProviderRequestLocationFactory
from django.test import RequestFactory
from django.urls import reverse
from waffle.testutils import override_flag

import pytest


@pytest.mark.django_db
@override_flag("provider_request", active=True)
def test_provider_portal_home_view_returns_only_unapproved_requests(client):
    # given: 1 pending provider request
    pr1 = ProviderRequestFactory.create(status=ProviderRequestStatus.PENDING_REVIEW)
    user = pr1.created_by

    # given: 1 approved provider request
    pr2 = ProviderRequestFactory.create(created_by=user)
    # location needs to exist in order to approve a PR
    loc = ProviderRequestLocationFactory(request=pr2)
    hp = pr2.approve()

    # when: ProviderPortalHomeView is accessed by the user
    request = RequestFactory().get(reverse("provider_portal_home"))
    request.user = user
    view = ProviderPortalHomeView()
    view.request = request
    qs = view.get_queryset()

    # then: only 1 unapproved request is rendered
    assert qs["requests"].get() == pr1
    # then: 1 hosting provider is rendered
    assert qs["providers"].get() == hp
