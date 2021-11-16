from apps.accounts.models.hosting import Hostingprovider
from typing import List
import pytest
import markdown
from django import urls
from django.contrib.auth import models as auth_models
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


class TestHostingProviderAdmin:
    """
    A test class for testing we can access the hosting provider
    page use the custom features
    """

    def _setup_hosting_provider(
        self, provider: Hostingprovider, default_user_groups: List[auth_models.Group]
    ) -> List:
        """
        Accept a  user linked to this provider with the correct groups
        """
        admin_grp, provider_grp = default_user_groups
        provider_user = provider.user_set.first()
        provider_user.save()
        provider_user.groups.add(provider_grp)
        provider_user.save()
        provider_grp.save()
        return [provider, provider_user]

    def test_visit_admin_create_page_for_user(
        self, db, client, sample_hoster_user, default_user_groups
    ):
        """
        Sign in, and visit new hosting page.
        Simulate the journey for a new user visiting the page to
        create a hosting provider
        """
        admin_grp, provider_grp = default_user_groups
        sample_hoster_user.save()
        sample_hoster_user.groups.add(provider_grp)
        sample_hoster_user.save()
        provider_grp.save()
        client.force_login(sample_hoster_user)

        admin_url = urls.reverse("greenweb_admin:accounts_hostingprovider_add")
        resp = client.get(admin_url)
        assert resp.status_code == 200

    def test_visit_admin_create_for_user_with_one_provider(
        self, db, client, hosting_provider_with_sample_user, default_user_groups
    ):
        """
        Simulate the journey for a user visiting the page to create
        a second hosting provider
        """
        provider, provider_user = self._setup_hosting_provider(
            hosting_provider_with_sample_user, default_user_groups
        )

        client.force_login(provider_user)

        admin_url = urls.reverse("greenweb_admin:accounts_hostingprovider_add")
        resp = client.get(admin_url)
        assert resp.status_code == 200

    def test_visit_admin_change_page_for_user_with_one_provider(
        self, db, client, hosting_provider_with_sample_user, default_user_groups
    ):
        """
        Simulate the user visiting a page to update their own provider
        """
        provider, provider_user = self._setup_hosting_provider(
            hosting_provider_with_sample_user, default_user_groups
        )

        client.force_login(provider_user)

        admin_url = urls.reverse(
            "greenweb_admin:accounts_hostingprovider_change", args=[provider.id],
        )
        resp = client.get(admin_url)
        assert resp.status_code == 200

    def test_preview_email_page_for_user_with_provider(
        self, db, client, hosting_provider_with_sample_user, default_user_groups
    ):
        """
        Test that we can visit an email preview page from the a provider admin page
        """

        # make sure we have one email template to refer to
        msg = ac_models.SupportMessage.objects.create(
            category="welcome-email",
            subject="hello, {{user}}",
            body="""
                Some content here, including the {{ user }}
            """,
        )

        provider, provider_user = self._setup_hosting_provider(
            hosting_provider_with_sample_user, default_user_groups
        )

        client.force_login(provider_user)
        admin_url = urls.reverse(
            "greenweb_admin:accounts_hostingprovider_preview_email", args=[provider.id],
        )
        resp = client.get(admin_url, {"email": msg.id})
        assert resp.status_code == 200

        # TODO check that we have our host and user present in the form

    def test_send_created_email_for_user_with_provider(
        self,
        db,
        client,
        hosting_provider_with_sample_user,
        default_user_groups,
        mailoutbox,
    ):
        """Test that an email can be sent with the information we submit in the form"""

        # create template email
        msg = ac_models.SupportMessage.objects.create(
            category="welcome-email",
            subject="hello, {{user}}",
            body="""
                Some content here, including the {{ user }}
            """,
        )
        provider, provider_user = self._setup_hosting_provider(
            hosting_provider_with_sample_user, default_user_groups
        )

        client.force_login(provider_user)
        admin_url = urls.reverse(
            "greenweb_admin:accounts_hostingprovider_send_email", args=[provider.id],
        )

        resp = client.post(
            admin_url,
            {
                "title": "A sample email subject",
                "recipient": [provider_user.email],
                "body": "Some content goes here",
                "message_type": msg.category,
                "provider": provider.id,
            },
            follow=True,
        )
        assert resp.status_code == 200

        # check email exists
        assert len(mailoutbox) == 1
        eml = mailoutbox[0]

        # check our email looks how we expect
        assert eml.body == "Some content goes here"
        assert eml.subject == "A sample email subject"

        # do we have the markdown representation too?
        html_alternative, *rest = [
            message for message in eml.alternatives if message[1] == "text/html"
        ]

        assert html_alternative[0] == markdown.markdown("Some content goes here")

    def test_log_created_email_for_user_with_provider_as_note(
        self,
        db,
        client,
        hosting_provider_with_sample_user,
        default_user_groups,
        mailoutbox,
    ):
        """Test that an email can be sent with the information we submit in the form"""

        # create template email
        msg = ac_models.SupportMessage.objects.create(
            category="welcome-email",
            subject="hello, {{user}}",
            body="""
                Some content here, including the {{ user }}
            """,
        )
        provider, provider_user = self._setup_hosting_provider(
            hosting_provider_with_sample_user, default_user_groups
        )

        client.force_login(provider_user)
        admin_url = urls.reverse(
            "greenweb_admin:accounts_hostingprovider_send_email", args=[provider.id],
        )

        resp = client.post(
            admin_url,
            {
                "title": "A sample email subject",
                "recipient": [provider_user.email],
                "body": "Some content goes here",
                "message_type": msg.category,
                "provider": provider.id,
            },
            follow=True,
        )
        assert resp.status_code == 200

        # check that we have our note for this provider
        labels = provider.staff_labels.all()
        assert len(labels) == 1
        assert labels[0].name == "welcome-email sent"

    @pytest.mark.parametrize(
        "archived", ((True, 0), (False, 1),),
    )
    def test_archived_users_hidden_by_default(
        self, db, client, hosting_provider_with_sample_user, archived
    ):
        """Test that by default, archived users to not show up in our listings."""

        hosting_provider_with_sample_user.archived = archived[0]
        hosting_provider_with_sample_user.save()
        client.force_login(hosting_provider_with_sample_user.user_set.first())

        admin_url = urls.reverse("greenweb_admin:accounts_hostingprovider_changelist")
        resp = client.get(admin_url, follow=True)

        assert len(resp.context["results"]) == archived[1]
        assert resp.status_code == 200

