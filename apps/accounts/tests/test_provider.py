import pytest

from django.urls import reverse
from waffle.testutils import override_flag
from apps.greencheck.factories import UserFactory


@pytest.mark.django_db
@override_flag("provider_request", active=True)
def test_edit_view_accessible_by_user_with_required_perms(
    client, hosting_provider_with_sample_user, sample_hoster_user
):
    # given: existing hosting provider with assigned user
    # when: accessing its edit view by that user
    client.force_login(sample_hoster_user)
    response = client.get(
        reverse("provider_edit", args=[str(hosting_provider_with_sample_user.id)])
    )

    # then: page for the correct provider request is rendered
    assert response.status_code == 200


@pytest.mark.django_db
@override_flag("provider_request", active=True)
def test_edit_view_accessible_by_admins(
    client, hosting_provider_with_sample_user, greenweb_staff_user
):
    # given: existing hosting provider with assigned user
    # when: accessing its edit view by GWF staff
    client.force_login(greenweb_staff_user)
    response = client.get(
        reverse("provider_edit", args=[str(hosting_provider_with_sample_user.id)])
    )

    # then: page for the correct provider request is rendered
    assert response.status_code == 200


@pytest.mark.django_db
@override_flag("provider_request", active=True)
def test_edit_view_inaccessible_by_unauthorized_users(
    client, hosting_provider_with_sample_user
):
    # given: existing hosting provider with assigned user
    # when: accessing its edit view by another user
    another_user = UserFactory.build()
    another_user.save()

    client.force_login(another_user)
    response = client.get(
        reverse("provider_edit", args=[str(hosting_provider_with_sample_user.id)])
    )

    # then: user is redirected to the provider portal
    assert response.status_code == 302
