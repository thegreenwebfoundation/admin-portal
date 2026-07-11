import pytest

from django import urls


@pytest.mark.django_db
def test_explorer_regular_user_cannot_access(sample_hoster_user, client):
    """
    Normal non staff users should not have access to the explorer application.
    """
    client.force_login(sample_hoster_user)
    explorer_url = urls.reverse("explorer_index")

    response = client.get(explorer_url)

    # explorer doesn't serve 403 responses when a user might have
    # access to the admin, but not the rights to access the explorer
    assert "not authorized to access this page" in response.content.decode("utf8")


@pytest.mark.django_db
def test_explorer_staff_user_can_access(greenweb_staff_user, client):
    """
    Internal staff users should have access to the explorer application however
    """
    client.force_login(greenweb_staff_user)
    explorer_url = urls.reverse("explorer_index")

    response = client.get(explorer_url)

    assert response.status_code == 200
    # we can't just rely on having a 200, as described before
    assert "not authorized to access this page" not in response.content.decode("utf8")


@pytest.mark.django_db
def test_explorer_anonymous_user_does_not_500(client):
    """
    Given an anonymous user, when they access the explorer index,
    then they are presented with the admin login page and no 500 error is raised.
    The EXPLORER_PERMISSION_VIEW lambda calls request.user.is_admin, which
    would previously raise AttributeError on AnonymousUser.
    """
    explorer_url = urls.reverse("explorer_index")
    response = client.get(explorer_url)

    content = response.content.decode("utf8")
    assert response.status_code == 200
    assert "Log in | Django site admin" in content
