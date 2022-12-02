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
