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
    # given: 1 pending verification request
    pr1 = ProviderRequestFactory.create(status=ProviderRequestStatus.PENDING_REVIEW)
    user = pr1.created_by

    # given: 1 approved verification request
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

    # then: only 1 unapproved verification request is rendered
    assert qs["requests"].get() == pr1
    # then: 1 hosting provider is rendered
    assert qs["providers"].get() == hp


@pytest.mark.django_db
@override_flag("provider_request", active=True)
def test_provider_portal_home_view_filters_out_removed_requests(client):
    # given: 1 removed verification request
    removed_request = ProviderRequestFactory.create(
        status=ProviderRequestStatus.REMOVED
    )
    # we need to access the user for creating the second verifcation request
    # and to visit as that user
    user = removed_request.created_by

    # given: 1 approved verification request
    pending_request = ProviderRequestFactory.create(
        created_by=user, status=ProviderRequestStatus.PENDING_REVIEW
    )

    # when: ProviderPortalHomeView is accessed by the user
    request = RequestFactory().get(reverse("provider_portal_home"))
    request.user = user
    view = ProviderPortalHomeView()
    view.request = request
    qs = view.get_queryset()

    # then: only the 1 pending verification request is displayed in the page
    assert pending_request in qs["requests"]
    assert removed_request not in qs["requests"]


@pytest.mark.django_db
@override_flag("provider_request", active=True)
def test_provider_portal_home_view_items_sorted_by_name(client):
    # given: 3 pending verification requests
    pr1 = ProviderRequestFactory.create(status=ProviderRequestStatus.PENDING_REVIEW)
    user = pr1.created_by
    pr2 = ProviderRequestFactory.create(
        status=ProviderRequestStatus.PENDING_REVIEW, created_by=user
    )
    pr3 = ProviderRequestFactory.create(
        status=ProviderRequestStatus.PENDING_REVIEW, created_by=user
    )

    # given: 3 approved verification request
    pr4 = ProviderRequestFactory.create(created_by=user)
    pr5 = ProviderRequestFactory.create(created_by=user)
    pr6 = ProviderRequestFactory.create(created_by=user)
    # location needs to exist in order to approve a PR
    ProviderRequestLocationFactory(request=pr4)
    ProviderRequestLocationFactory(request=pr5)
    ProviderRequestLocationFactory(request=pr6)
    hp4 = pr4.approve()
    hp5 = pr5.approve()
    hp6 = pr6.approve()

    # when: ProviderPortalHomeView is accessed by the user
    request = RequestFactory().get(reverse("provider_portal_home"))
    request.user = user
    view = ProviderPortalHomeView()
    view.request = request
    qs = view.get_queryset()

    # then: verification requests are sorted by name
    assert list(qs["requests"]) == sorted(qs["requests"], key=lambda item: item.name)
    # then: hosting providers are sorted by name
    assert list(qs["providers"]) == sorted(qs["providers"], key=lambda item: item.name)
