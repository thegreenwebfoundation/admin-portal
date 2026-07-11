from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import APIKey, APIService
from apps.greencheck import factories as gc_factories

import pytest


@pytest.mark.django_db
def test_request_without_shared_secret(client, mocker):
    """
    Attempting to introspect a key without providing a shared secret
    gives an unauthorized response
    """

    # GIVEN I do not provide a shared secret
    mock_settings = mocker.patch("apps.accounts.permissions.settings")
    mock_settings.GWF_SHARED_SECRET = "abc123"
    user = gc_factories.UserFactory.create()
    service = APIService.objects.create(name="Test service", key="test_service")
    (_key, token) = APIKey.objects.create_key_for_user(user, service, "motivation statement")
    body = { "token": token }
    headers = { }

    # WHEN I make a request to the introspection endpoint
    response = client.post(reverse("internal-introspect-api-key"), body, headers=headers)

    # THEN I receive an unauthorized response
    assert response.status_code == 401

@pytest.mark.django_db
def test_request_with_incorrect_shared_secret(client, mocker):
    """
    Attempting to introspect a key while providing an incorrect
    shared secret gives an unauthorized response
    """

    # GIVEN I provide an incorrect shared secret
    mock_settings = mocker.patch("apps.accounts.permissions.settings")
    mock_settings.GWF_SHARED_SECRET = "abc123"
    user = gc_factories.UserFactory.create()
    service = APIService.objects.create(name="Test service", key="test_service")
    (_key, token) = APIKey.objects.create_key_for_user(user, service, "motivation statement")
    body = { "token": token }
    headers = { "X-GWF-Shared-Secret": "def456" }

    # WHEN I make a request to the introspection endpoint
    response = client.post(reverse("internal-introspect-api-key"), body, headers=headers)

    # THEN I receive an unauthorized response
    assert response.status_code == 401




@pytest.mark.django_db
def test_request_for_valid_api_key_with_correct_shared_secret(client, mocker):
    """
    Attempting to introspect a valid key while providing a correct
    shared secret gives an active response
    """

    # GIVEN I provide a correct shared secret and a valid API key
    mock_settings = mocker.patch("apps.accounts.permissions.settings")
    mock_settings.GWF_SHARED_SECRET = "abc123"
    user = gc_factories.UserFactory.create()
    service = APIService.objects.create(name="Test service", key="test_service")
    (key, token) = APIKey.objects.create_key_for_user(user, service, "motivation statement")
    body = { "token": token }
    headers = { "X-GWF-Shared-Secret": mock_settings.GWF_SHARED_SECRET }

    # WHEN I make a request to the introspection endpoint
    response = client.post(reverse("internal-introspect-api-key"), body, headers=headers)

    # THEN I receive an "active" response
    assert response.status_code == 200
    body = response.json()
    assert body["active"]
    assert body["user_id"] == user.id
    assert body["username"] == user.username
    assert body["expiry_date"] == key.expiry_date
    assert body["prefix"] == key.prefix
    assert body["service"] == service.key

@pytest.mark.django_db
def test_request_for_wrong_api_key_with_correct_shared_secret(client, mocker):
    """
    Attempting to introspect an invalid key while providing a correct
    shared secret gives an inactive response
    """

    # GIVEN I provide a correct shared secret and an invalid API key
    mock_settings = mocker.patch("apps.accounts.permissions.settings")
    mock_settings.GWF_SHARED_SECRET = "abc123"
    user = gc_factories.UserFactory.create()
    service = APIService.objects.create(name="Test service", key="test_service")
    (_key, token) = APIKey.objects.create_key_for_user(user, service, "motivation statement")
    body = { "token": "cde3456" }
    headers = { "X-GWF-Shared-Secret": mock_settings.GWF_SHARED_SECRET }

    # WHEN I make a request to the introspection endpoint
    response = client.post(reverse("internal-introspect-api-key"), body, headers=headers)

    # THEN I receive an "inactive" response
    assert response.status_code == 200
    body = response.json()
    assert not body["active"]
    assert "user_id" not in body
    assert "username" not in body
    assert "expiry_date" not in body
    assert "prefix" not in body

@pytest.mark.django_db
def test_request_for_expired_api_key_with_correct_shared_secret(client, mocker):
    """
    Attempting to introspect an expired key while providing a correct
    shared secret gives an inactive response
    """

    # GIVEN I provide a correct shared secret and an expired API key
    mock_settings = mocker.patch("apps.accounts.permissions.settings")
    mock_settings.GWF_SHARED_SECRET = "abc123"
    user = gc_factories.UserFactory.create()
    service = APIService.objects.create(name="Test service", key="test_service")
    (_key, token) = APIKey.objects.create_key_for_user(
            user, service, "motivation statement",
            expiry_date = timezone.now() - timedelta(days=1)
    )
    body = { "token": token }
    headers = { "X-GWF-Shared-Secret": mock_settings.GWF_SHARED_SECRET }

    # WHEN I make a request to the introspection endpoint
    response = client.post(reverse("internal-introspect-api-key"), body, headers=headers)

    # THEN I receive an "inactive" response
    assert response.status_code == 200
    body = response.json()
    assert not body["active"]
    assert "user_id" not in body
    assert "username" not in body
    assert "expiry_date" not in body
    assert "prefix" not in body


@pytest.mark.django_db
def test_request_for_revoked_api_key_with_correct_shared_secret(client, mocker):
    """
    Attempting to introspect a revoked key while providing a correct
    shared secret gives an inactive response
    """

    # GIVEN I provide a correct shared secret and a revoked API key
    mock_settings = mocker.patch("apps.accounts.permissions.settings")
    mock_settings.GWF_SHARED_SECRET = "abc123"
    user = gc_factories.UserFactory.create()
    service = APIService.objects.create(name="Test service", key="test_service")
    (key, token) = APIKey.objects.create_key_for_user(user, service, "motivation statement")
    key.revoked = True
    key.save()
    body = { "token": token }
    headers = { "X-GWF-Shared-Secret": mock_settings.GWF_SHARED_SECRET }

    # WHEN I make a request to the introspection endpoint
    response = client.post(reverse("internal-introspect-api-key"), body, headers=headers)

    # THEN I receive an "inactive" response
    assert response.status_code == 200
    body = response.json()
    assert not body["active"]
    assert "user_id" not in body
    assert "username" not in body
    assert "expiry_date" not in body
    assert "prefix" not in body

@pytest.mark.django_db
def test_request_for_active_api_key_with_correct_shared_secret_for_banned_juser(client, mocker):
    """
    Attempting to introspect an active key for a banned user while
    providing a correct shared secret gives an inactive response
    """

    # GIVEN I provide a correct shared secret and an active API key for a banned user.
    mock_settings = mocker.patch("apps.accounts.permissions.settings")
    mock_settings.GWF_SHARED_SECRET = "abc123"
    user = gc_factories.UserFactory.create()
    service = APIService.objects.create(name="Test service", key="test_service")
    (_key, token) = APIKey.objects.create_key_for_user(user, service, "motivation statement")
    user.api_access_banned = True
    user.save()
    body = { "token": token }
    headers = { "X-GWF-Shared-Secret": mock_settings.GWF_SHARED_SECRET }

    # WHEN I make a request to the introspection endpoint
    response = client.post(reverse("internal-introspect-api-key"), body, headers=headers)

    # THEN I receive an "inactive" response
    assert response.status_code == 200
    body = response.json()
    assert not body["active"]
    assert "user_id" not in body
    assert "username" not in body
    assert "expiry_date" not in body
    assert "prefix" not in body

