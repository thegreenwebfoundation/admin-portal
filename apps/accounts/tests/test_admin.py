import pytest
from django import urls

from .. import admin as ac_admin
from .. import admin_site
from .. import models as ac_models


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
        admin_grp, provider_grp = default_user_groups
        sample_hoster_user.save()
        sample_hoster_user.groups.add(provider_grp)
        sample_hoster_user.save()
        provider_grp.save()
        client.force_login(sample_hoster_user)

        new_provider_url = urls.reverse("greenweb_admin:accounts_hostingprovider_add")
        resp = client.get(new_provider_url)
        assert resp.status_code == 200


class TestDatacenterAdmin:
    def test_visit_admin_page(
        self, db, client, sample_hoster_user, default_user_groups
    ):
        """
        Sign in, and visit new datacenter page.

        Simulate the journey for a new user creating a datacenter in the admin
        """
        admin_grp, provider_grp = default_user_groups
        sample_hoster_user.save()
        sample_hoster_user.groups.add(provider_grp)
        sample_hoster_user.save()
        provider_grp.save()
        client.force_login(sample_hoster_user)

        new_datacenter_url = urls.reverse("greenweb_admin:accounts_datacenter_add")
        resp = client.get(new_datacenter_url)
        assert resp.status_code == 200

    def test_update_datacenter_admin_page(
        self, db, client, sample_hoster_user, datacenter, default_user_groups
    ):
        """
        Sign in, and visit new datacenter page.

        Simulate the journey for a new user creating a datacenter in the admin
        """
        admin_grp, provider_grp = default_user_groups

        # check  we have everything persisted
        sample_hoster_user.save()

        # associated users, and objects with each other
        sample_hoster_user.groups.add(provider_grp)
        datacenter.user = sample_hoster_user
        datacenter.save()
        provider_grp.save()

        # now log in
        client.force_login(sample_hoster_user)

        dc_update_path = urls.reverse(
            "greenweb_admin:accounts_datacenter_change", args=[datacenter.id]
        )
        resp = client.get(dc_update_path)
        assert resp.status_code == 200

    def test_get_inlines_staff(
        self,
        db,
        rf,
        sample_hoster_user,
        hosting_provider,
        datacenter,
        default_user_groups,
    ):
        admin_grp, provider_grp = default_user_groups

        hosting_provider.save()
        sample_hoster_user.hostingprovider = hosting_provider
        sample_hoster_user.groups.add(admin_grp)
        sample_hoster_user.save()
        admin_grp.save()

        gcip_admin = ac_admin.DatacenterAdmin(
            ac_models.Datacenter, admin_site.greenweb_admin
        )

        ip_range_listing_path = urls.reverse(
            "greenweb_admin:accounts_datacenter_change", args=[datacenter.id]
        )
        request = rf.get(ip_range_listing_path)
        request.user = sample_hoster_user

        inlines = gcip_admin.get_inlines(request, datacenter)

        assert ac_admin.DatacenterNoteInline in inlines

    def test_get_inlines_non_staff(
        self, db, rf, sample_hoster_user, hosting_provider, datacenter
    ):
        hosting_provider.save()
        sample_hoster_user.hostingprovider = hosting_provider
        sample_hoster_user.save()

        gcip_admin = ac_admin.DatacenterAdmin(
            ac_models.Datacenter, admin_site.greenweb_admin
        )

        dc_update_path = urls.reverse(
            "greenweb_admin:accounts_datacenter_change", args=[datacenter.id]
        )
        request = rf.get(dc_update_path)
        request.user = sample_hoster_user

        inlines = gcip_admin.get_inlines(request, datacenter)

        assert ac_admin.DatacenterNoteInline not in inlines

