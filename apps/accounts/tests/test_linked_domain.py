import pytest
from django import urls
from django.core.exceptions import ValidationError
from guardian.shortcuts import assign_perm
from apps.greencheck.factories import (
    UserFactory,
)
from apps.accounts import models, views
from apps.accounts.permissions import manage_provider

@pytest.mark.django_db
def test_create_linked_domain_happy_path(user, hosting_provider_factory, client, mocker):
    """
    Test creating a linked domain for a provider,
    where the provider has a valid carbontxt file
    """

    #GIVEN a hosting provider, and a domain with a valid carbon.txt
    domain = "example.com"
    is_primary = "True"
    provider = hosting_provider_factory(created_by=user)
    assign_perm(manage_provider.codename, user, provider)
    form_data = [
        {
            "provider_domain_create_view-current_step": "0",
            "0-domain": domain,
            "0-is_primary": is_primary,
        }, {
            "provider_domain_create_view-current_step": "1",
        }
    ]
    mock_validator = mocker.patch(
        "apps.accounts.views.validate_carbon_txt_for_domain",
        return_value=True
    )

    #WHEN I link the domain to the provider
    client.force_login(user)
    for step_data in form_data:
        response = client.post(
            urls.reverse("provider-domain-create", args=[provider.id]),
            step_data, follow=True
        )

    #THEN I should be returned to the domains list for the provider
    assert response.resolver_match.func.view_class is views.ProviderDomainsView

    # AND a new LinkedDomain should exist for the given provider and domain,
    # in the PENDING_REVIEW state
    ld = models.LinkedDomain.objects.get()
    assert ld.domain == domain
    assert ld.created_by == user
    assert ld.provider == provider
    assert ld.state == models.LinkedDomainState.PENDING_REVIEW
    assert ld.is_primary

@pytest.mark.django_db
def test_create_linked_domain_unvalidated(user, hosting_provider_factory, client, mocker):
    """
    Test creating a linked domain for a provider,
    where the provider does not have a valid carbontxt file
    """

    #GIVEN a hosting provider, and a domain without a valid carbon.txt
    domain = "example.com"
    is_primary = "True"
    provider = hosting_provider_factory(created_by=user)
    assign_perm(manage_provider.codename, user, provider)
    form_data = [
        {
            "provider_domain_create_view-current_step": "0",
            "0-domain": domain,
            "0-is_primary": is_primary,
        }, {
            "provider_domain_create_view-current_step": "1",
        }
    ]
    mock_validator = mocker.patch(
        "apps.accounts.views.validate_carbon_txt_for_domain",
        side_effect=ValidationError("Something went wrong validating the domain")
    )

    #WHEN I link the domain to the provider
    client.force_login(user)
    for step_data in form_data:
        response = client.post(
            urls.reverse("provider-domain-create", args=[provider.id]),
            step_data, follow=True
        )

    #THEN I should be remain on the last page of the creation wizard
    assert response.resolver_match.func.view_class is views.ProviderDomainCreateView

    # AND no new LinkedDomain should exist for the given provider and domain,
    ld = models.LinkedDomain.objects.filter(provider_id=provider.pk, domain=domain)
    assert not ld


@pytest.mark.django_db
def test_create_linked_domain_unauthorized(user, hosting_provider_factory, client, mocker):
    """
    Test creating a linked domain for a provider,
    where the user has no permissions for the provider
    """

    #GIVEN a hosting provider, a domain with a valid carbon.txt
    # and a user without permissions on that provider

    domain = "example.com"
    is_primary = "True"
    provider = hosting_provider_factory()
    form_data = [
        {
            "provider_domain_create_view-current_step": "0",
            "0-domain": domain,
            "0-is_primary": is_primary,
        }, {
            "provider_domain_create_view-current_step": "1",
        }
    ]
    mock_validator = mocker.patch(
        "apps.accounts.views.validate_carbon_txt_for_domain",
        return_value=True
    )

    #WHEN I link the domain to the provider
    client.force_login(user)
    for step_data in form_data:
        response = client.post(
            urls.reverse("provider-domain-create", args=[provider.id]),
            step_data, follow=True
        )

    # Then I should be forbidden from acccessing the page
    assert response.status_code == 403

    # AND no new LinkedDomain should exist for the given provider and domain,
    ld = models.LinkedDomain.objects.filter(provider_id=provider.pk, domain=domain)
    assert not ld


@pytest.mark.django_db
def test_delete_linked_domain_happy_path(user, hosting_provider_factory, linked_domain_factory, client):
    """
    Test deleting a linked domain for a provider,
    where the logged in user has permissions for provider
    """

    # GIVEN a provider owned by the logged in user
    # AND a linked domain for that provider
    provider = hosting_provider_factory(created_by=user)
    domain = "example.com"
    assign_perm(manage_provider.codename, user, provider)
    ld = linked_domain_factory(created_by=user, domain=domain, provider=provider)
    # WHEN I delete the linked domain
    client.force_login(user)
    response = client.post(urls.reverse("provider-domain-delete", args=[provider.id, domain]), {}, follow=True)

    #THEN I should be returned to the domains list for the provider
    assert response.resolver_match.func.view_class is views.ProviderDomainsView

    # AND no LinkedDomain should exist for the given provider and domain,
    ld = models.LinkedDomain.objects.filter(provider_id=provider.pk, domain=domain)
    assert not ld

@pytest.mark.django_db
def test_delete_linked_domain_unauthorized(user, hosting_provider_factory, linked_domain_factory, client):
    """
    Test deleting a linked domain for a provider,
    where the logged in user has no permissions for provider
    """

    # GIVEN a provider not owned by the logged in user
    # AND a linked domain for that provider
    provider = hosting_provider_factory()
    domain = "example.com"
    ld = linked_domain_factory(created_by=user, domain=domain, provider=provider)

    # WHEN I delete the linked domain
    client.force_login(user)
    response = client.post(urls.reverse("provider-domain-delete", args=[provider.id, domain]), {}, follow=True)

    #THEN I should be forbidden from making the request
    assert response.status_code == 403

    # AND the LinkedDomain should still exist for the given provider and domain,
    ld = models.LinkedDomain.objects.filter(provider_id=provider.pk, domain=domain)
    assert ld

