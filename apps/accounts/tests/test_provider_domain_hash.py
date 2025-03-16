import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from ...greencheck.exceptions import NoSharedSecret
from ..models.hosting import DOMAIN_HASH_ISSUER_ID


def test_create_domain_hash_success(db, user_with_provider):
    domain = "example.com"
    provider = user_with_provider.hosting_providers.first()
    provider.refresh_shared_secret()

    domain_hash = provider.create_domain_hash(domain, user_with_provider)

    assert domain_hash is not None
    assert domain_hash.created_by == user_with_provider
    assert domain_hash.provider == provider
    assert domain_hash.domain == domain

    domain_hash.hash.startswith(DOMAIN_HASH_ISSUER_ID)
    just_hash_content = domain_hash.hash.replace(f"{DOMAIN_HASH_ISSUER_ID}-", "")
    assert len(just_hash_content) == 64


def test_create_domain_hash_no_user(db, user_with_provider):
    domain = "example.com"
    provider = user_with_provider.hosting_providers.first()
    provider.refresh_shared_secret()

    # check if this the correct kind of error for django
    with pytest.raises(ValueError, match="A user must be associated with the provider"):
        provider.create_domain_hash(domain, None)


def test_create_domain_hash_user_no_permission(db, user_with_provider, user_factory):
    random_user = user_factory.create()

    domain = "example.com"
    provider = user_with_provider.hosting_providers.first()
    provider.refresh_shared_secret()

    with pytest.raises(
        PermissionDenied, match="User does not have permission to update this provider"
    ):
        provider.create_domain_hash(domain, random_user)


def test_create_domain_hash_invalid_domain(db, user_with_provider):
    invalid_domain = "not_a_real_domain"
    provider = user_with_provider.hosting_providers.first()
    provider.refresh_shared_secret()

    with pytest.raises(ValidationError, match="Invalid domain provided"):
        provider.create_domain_hash(invalid_domain, user_with_provider)


def test_create_domain_hash_missing_shared_secret(db, user_with_provider):
    domain = "example.com"
    provider = user_with_provider.hosting_providers.first()

    # Do not refresh shared secret to simulate missing shared secret

    with pytest.raises(NoSharedSecret):
        provider.create_domain_hash(domain, user_with_provider)


def test_create_domain_hash_duplicate_hash(db, user_with_provider):
    domain = "example.com"
    provider = user_with_provider.hosting_providers.first()
    provider.refresh_shared_secret()

    # Create the first hash
    provider.create_domain_hash(domain, user_with_provider)

    # Attempt to create a duplicate hash
    with pytest.raises(
        ValueError, match="Domain hash already exists for this domain and provider"
    ):
        provider.create_domain_hash(domain, user_with_provider)
