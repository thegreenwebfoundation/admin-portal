from django.urls import reverse
from waffle.testutils import override_flag

import pytest


@pytest.mark.django_db
def test_directory(client):
    """
    Confirm that the directory view is accessible when our flag is active
    """
    # when: the directory is accessed with an active flag
    res = client.get(reverse("directory-index"))

    # then: we see a successful response
    assert res.status_code == 200


@pytest.mark.django_db
def test_ordering_of_providers_in_directory(client, hosting_provider_factory):
    """
    Check that providers are listed in order of the name of their
    country, to allow for grouping by country in templates
    """
    german_provider = hosting_provider_factory.create(country="DE", showonwebsite=True)
    danish_provider = hosting_provider_factory.create(country="DK", showonwebsite=True)

    # when: the directory is accessed with an active flag
    res = client.get(reverse("directory-index"))

    # then: we see a successful response
    assert res.status_code == 200

    # and: the providers are listed in order of their country name
    assert res.context["ordered_results"][0] == danish_provider
    assert res.context["ordered_results"][1] == german_provider


@pytest.mark.django_db
def test_templates_in_filter_view(client, hosting_provider_factory):
    """
    Check that we include the no_directoru results in our template
    """

    # given: a hosting provider in Germany
    hosting_provider_factory.create(country="DE", showonwebsite=True)

    # when: we visit our directory
    res = client.get(reverse("directory-index"))

    # then: we should get a successful response
    assert res.status_code == 200

    # and: we should see the "has results" template in our list of templates
    # in use
    templates = [tpl.name for tpl in res.templates]
    assert "greencheck/partials/_directory_results.html" in templates

@pytest.mark.django_db
def test_carbon_txt_template_included_for_provider_with_carbon_txt(client, hosting_provider_factory):
    """
    Check that we include the carbon_txt badge when a provider has a carbon_txt url
    """

    # given: a hosting provider in Germany
    hosting_provider_factory.create(country="DE", showonwebsite=True, carbon_txt_url="https://www.example.com/carbon.txt")

    # when: we visit our directory
    res = client.get(reverse("directory-index"))

    # then: we should get a successful response
    assert res.status_code == 200

    # and: we should see the "has results" template in our list of templates
    # in use
    templates = [tpl.name for tpl in res.templates]
    assert "greencheck/partials/_directory_carbon_txt_badge.html" in templates

@pytest.mark.django_db
def test_carbon_txt_template_not_included_for_provider_without_carbon_txt(client, hosting_provider_factory):
    """
    Check that we do not include the carbon_txt badge when a provider has no carbon_txt url
    """

    # given: a hosting provider in Germany
    hosting_provider_factory.create(country="DE", showonwebsite=True, carbon_txt_url=None)

    # when: we visit our directory
    res = client.get(reverse("directory-index"))

    # then: we should get a successful response
    assert res.status_code == 200

    # and: we should see the "has results" template in our list of templates
    # in use
    templates = [tpl.name for tpl in res.templates]
    assert "greencheck/partials/_directory_carbon_txt_badge.html" not in templates


@pytest.mark.django_db
def test_fallback_when_no_filter_view_has_no_results(client, hosting_provider_factory):
    """
    Check that we include the no_directoru results in our template
    """

    # given: a hosting provider in Germany
    hosting_provider_factory.create(country="DE", showonwebsite=True)

    # when: we filter our directory by another country, Denmark
    res = client.get(reverse("directory-index"), {"country": "DK"})

    # then: we should get a successful response
    assert res.status_code == 200

    # and: we should see the "no results" template in our list of templates
    # in use
    templates = [tpl.name for tpl in res.templates]
    assert "greencheck/partials/_directory_no_results.html" in templates
