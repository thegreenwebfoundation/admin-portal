from .. import admin as gc_admin
from .. import models
from ...accounts import admin_site
from .. import factories as gc_factories
from django import urls


class TestGreencheckIpApproveAdmin:
    def test_get_actions_staff_user(self, db, rf, sample_hoster_user, hosting_provider):
        """Check that a user with the correct privileges can"""

        hosting_provider.save()
        sample_hoster_user.is_staff = True
        sample_hoster_user.save()

        gcip_admin = gc_admin.GreencheckIpApproveAdmin(
            models.GreencheckIp, admin_site.greenweb_admin
        )

        ip_range_listing_path = urls.reverse(
            "greenweb_admin:greencheck_greencheckipapprove_changelist"
        )
        request = rf.get(ip_range_listing_path)
        request.user = sample_hoster_user

        actions = gcip_admin.get_actions(request)

        assert "approve_selected" in actions

    def test_get_actions_non_staff_user(
        self, db, rf, sample_hoster_user, hosting_provider
    ):
        """Check that a sample"""

        hosting_provider.save()

        gcip_admin = gc_admin.GreencheckIpApproveAdmin(
            models.GreencheckIp, admin_site.greenweb_admin
        )

        ip_range_listing_path = urls.reverse(
            "greenweb_admin:greencheck_greencheckipapprove_changelist"
        )
        request = rf.get(ip_range_listing_path)
        request.user = sample_hoster_user

        actions = gcip_admin.get_actions(request)

        assert "approve_selected" not in actions

    def test_get_queryset_staff(
        self, db, rf, sample_hoster_user, hosting_provider, green_ip
    ):
        hosting_provider.save()
        sample_hoster_user.is_staff = True
        sample_hoster_user.save()

        provider = gc_factories.HostingProviderFactory()
        gip = gc_factories.GreenIpFactory(hostingprovider=provider)
        assert hosting_provider.greencheckip_set.first() == green_ip

        gcip_admin = gc_admin.GreencheckIpApproveAdmin(
            models.GreencheckIp, admin_site.greenweb_admin
        )

        ip_range_listing_path = urls.reverse(
            "greenweb_admin:greencheck_greencheckipapprove_changelist"
        )
        request = rf.get(ip_range_listing_path)
        request.user = sample_hoster_user

        qs = gcip_admin.get_queryset(request)

        assert models.GreencheckIp.objects.count() == 2
        assert qs.count() == 2
        assert green_ip in qs
        assert gip in qs

    def test_get_queryset_non_staff(
        self,
        db,
        rf,
        hosting_provider_with_sample_user,
        green_ip,
    ):
        provider = gc_factories.HostingProviderFactory()
        gip = gc_factories.GreenIpFactory(hostingprovider=provider)

        assert hosting_provider_with_sample_user.greencheckip_set.first() == green_ip

        gcip_admin = gc_admin.GreencheckIpApproveAdmin(
            models.GreencheckIp, admin_site.greenweb_admin
        )

        ip_range_listing_path = urls.reverse(
            "greenweb_admin:greencheck_greencheckipapprove_changelist"
        )
        request = rf.get(ip_range_listing_path)
        request.user = hosting_provider_with_sample_user.users.first()

        assert not request.user.is_staff

        qs = gcip_admin.get_queryset(request)

        assert models.GreencheckIp.objects.count() == 2
        assert qs.count() == 1
        assert green_ip in qs
        assert gip not in qs
