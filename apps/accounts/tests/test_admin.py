from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from conftest import sample_hoster_user
from django import urls

import pytest


class TestHostingProviderAdminInlineRendering:
    """
    Test that we can visit new provider pages. This exercises
    any logic for deciding which inlines to show.
    """

    def test_visit_new_provider(
        self, db, client, sample_hoster_user, default_user_groups
    ):
        """
        Sign in, and visit new hosting provider page.

        Simulate the journey for a new user creating an hosting
        provider in the admin.
        """
        sample_hoster_user.save()
        client.force_login(sample_hoster_user)

        new_provider_url = urls.reverse("greenweb_admin:accounts_hostingprovider_add")
        resp = client.get(new_provider_url)
        assert resp.status_code == 200
