import json
import logging
import pathlib
from unittest.mock import MagicMock

import markdown
import pytest
from django import urls
from django.contrib.auth import models as auth_models
from guardian.shortcuts import assign_perm

from apps.accounts.models.hosting import Hostingprovider
from apps.accounts.permissions import manage_datacenter
from apps.greencheck.tests import setup_domains
from conftest import ProviderRequestFactory

from ...greencheck import domain_check
from .. import admin as ac_admin
from .. import admin_site
from .. import models as ac_models

checker = domain_check.GreenDomainChecker()


logger = logging.getLogger(__name__)


@pytest.fixture
def rdap_content():
    rdap_output_path = pathlib.Path(__file__).parent / "sample.rdap.output.json"
    return json.loads(rdap_output_path.read_text())


class TestDatacenterAdmin:
    def test_regular_user_cannot_create_new_dc(self, db, client, sample_hoster_user):
        """
        Regular users (i.e. that do not belong to the admin group)
        should not have access to adding new data centers via Django admin.
        """

        client.force_login(sample_hoster_user)

        admin_url = urls.reverse("greenweb_admin:accounts_datacenter_add")
        resp = client.get(admin_url)
        assert resp.status_code == 403

    def test_admin_can_create_new_dc(self, db, client, greenweb_staff_user):
        """
        Admin users should be able to create a new data center using the admin panel
        - for convenience purposes.
        """

        client.force_login(greenweb_staff_user)

        admin_url = urls.reverse("greenweb_admin:accounts_datacenter_add")
        resp = client.get(admin_url)
        assert resp.status_code == 200

    def test_update_datacenter_admin_page(
        self, db, client, sample_hoster_user, datacenter
    ):
        """
        Sign in, and visit the change view of the datacenter.

        Simulate the journey for a new user accessing a datacenter they have permissions to in the admin
        """
        datacenter.user = sample_hoster_user
        datacenter.save()
        assign_perm(manage_datacenter.codename, sample_hoster_user, datacenter)

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
        client,
        sample_hoster_user,
        greenweb_staff_user,
        hosting_provider,
        datacenter,
    ):
        """Check that a staff member can see the notes section for a datacenter"""
        hosting_provider.save()
        sample_hoster_user.hostingprovider = hosting_provider
        sample_hoster_user.save()
        hosting_provider.save()
        datacenter.user = sample_hoster_user
        datacenter.save()

        gcip_admin = ac_admin.DatacenterAdmin(
            ac_models.Datacenter, admin_site.greenweb_admin
        )

        ip_range_listing_path = urls.reverse(
            "greenweb_admin:accounts_datacenter_change", args=[datacenter.id]
        )
        client.force_login(sample_hoster_user)
        request = client.get(ip_range_listing_path)
        request.user = greenweb_staff_user

        inlines = gcip_admin.get_inlines(request, datacenter)
        fieldsets = gcip_admin.get_fieldsets(request, datacenter)

        fieldset_names = []
        for fieldset in fieldsets:
            name, fields = fieldset
            fieldset_names.append(name)

        # Then they should be able to edit which hosting providers
        # are associated with the datacentre, and leave notes for other
        # admin staff
        assert "Associated hosting providers" in fieldset_names
        assert ac_admin.DatacenterNoteInline in inlines

    def test_get_inlines_non_staff(
        self, db, rf, sample_hoster_user, hosting_provider, datacenter
    ):
        # Given: a end user running a datacentre or hosting provider
        hosting_provider.save()
        sample_hoster_user.hostingprovider = hosting_provider
        sample_hoster_user.save()

        gcip_admin = ac_admin.DatacenterAdmin(
            ac_models.Datacenter, admin_site.greenweb_admin
        )

        dc_update_path = urls.reverse(
            "greenweb_admin:accounts_datacenter_change", args=[datacenter.id]
        )
        # When: they visit a datacentre page
        request = rf.get(dc_update_path)
        request.user = sample_hoster_user

        # what fields and fieldets do we have on our change form?
        inlines = gcip_admin.get_inlines(request, datacenter)
        fieldsets = gcip_admin.get_fieldsets(request, datacenter)

        fieldset_names = []
        for fieldset in fieldsets:
            name, fields = fieldset
            fieldset_names.append(name)

        # Then: they should not be able to add other hosting providers
        # to the datacentre, or view internal administration notes
        assert ac_admin.DatacenterNoteInline not in inlines
        assert "Associated hosting providers" not in fieldset_names


class TestHostingProviderAdmin:
    """
    A test class for testing we can access the hosting provider
    page use the custom features
    """

    def test_regular_user_cannot_create_new_hp(self, db, client, sample_hoster_user):
        """
        Regular users (i.e. that do not belong to the admin group)
        should not have access to adding new hosting providers via Django admin.
        They should use the verification request flow instead.
        """

        client.force_login(sample_hoster_user)

        admin_url = urls.reverse("greenweb_admin:accounts_hostingprovider_add")
        resp = client.get(admin_url)
        assert resp.status_code == 403

    def test_admin_can_create_new_hp(self, db, client, greenweb_staff_user):
        """
        Admin users should be able to create a new hosting provider using the admin panel
        - for convenience purposes.
        """

        client.force_login(greenweb_staff_user)

        admin_url = urls.reverse("greenweb_admin:accounts_hostingprovider_add")
        resp = client.get(admin_url)
        assert resp.status_code == 200

    def test_visit_admin_change_page_for_user_with_one_provider(
        self, db, client, hosting_provider_with_sample_user
    ):
        """
        Simulate the user visiting a page to update their own provider
        """

        user = hosting_provider_with_sample_user.user_set.first()
        client.force_login(user)

        admin_url = urls.reverse(
            "greenweb_admin:accounts_hostingprovider_change",
            args=[hosting_provider_with_sample_user.id],
        )
        resp = client.get(admin_url)
        assert resp.status_code == 200

    def test_preview_email_page_for_user_with_provider(
        self, db, client, hosting_provider_with_sample_user
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

        user = hosting_provider_with_sample_user.user_set.first()
        client.force_login(user)
        admin_url = urls.reverse(
            "greenweb_admin:accounts_hostingprovider_preview_email",
            args=[hosting_provider_with_sample_user.id],
        )
        resp = client.get(admin_url, {"email": msg.id})
        assert resp.status_code == 200

        # TODO check that we have our host and user present in the form

    def test_send_created_email_for_user_with_provider(
        self,
        db,
        client,
        hosting_provider_with_sample_user,
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
        user = hosting_provider_with_sample_user.user_set.first()
        client.force_login(user)
        admin_url = urls.reverse(
            "greenweb_admin:accounts_hostingprovider_send_email",
            args=[hosting_provider_with_sample_user.id],
        )

        resp = client.post(
            admin_url,
            {
                "title": "A sample email subject",
                "recipient": [user.email],
                "body": "Some content goes here",
                "message_type": msg.category,
                "provider": hosting_provider_with_sample_user.id,
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
        user = hosting_provider_with_sample_user.user_set.first()

        client.force_login(user)
        admin_url = urls.reverse(
            "greenweb_admin:accounts_hostingprovider_send_email",
            args=[hosting_provider_with_sample_user.id],
        )

        resp = client.post(
            admin_url,
            {
                "title": "A sample email subject",
                "recipient": [user.email],
                "body": "Some content goes here",
                "message_type": msg.category,
                "provider": hosting_provider_with_sample_user.id,
            },
            follow=True,
        )
        assert resp.status_code == 200

        # check that we have our note for this provider
        labels = hosting_provider_with_sample_user.staff_labels.all()
        assert len(labels) == 1
        assert labels[0].name == "welcome-email sent"

    @pytest.mark.parametrize(
        "archived",
        (
            (True, 0),
            (False, 1),
        ),
    )
    def test_archived_providers_are_hidden_by_default(
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

    @pytest.mark.skip(reason="we handle this with a list filter option now")
    @pytest.mark.parametrize(
        "archived",
        (
            (True, 1),
            (False, 0),
        ),
    )
    def test_archived_providers_hidden_by_seen_with_override_params(
        self, db, client, hosting_provider_with_sample_user, archived
    ):
        """
        If we really need to see archived users, we can with a
        special GET param, to override our view
        """

        hosting_provider_with_sample_user.archived = archived[0]
        hosting_provider_with_sample_user.save()
        client.force_login(hosting_provider_with_sample_user.user_set.first())

        admin_url = urls.reverse("greenweb_admin:accounts_hostingprovider_changelist")
        resp = client.get(admin_url, {"archived": True}, follow=True)

        assert len(resp.context["results"]) == archived[1]
        assert resp.status_code == 200

    def test_staff_can_remove_provider_from_user(
        self, db, client, hosting_provider_with_sample_user, greenweb_staff_user
    ):
        """
        Can a staff member update a user to remove them
        from a given hosting provider?
        """

        user = hosting_provider_with_sample_user.user_set.first()
        provider = hosting_provider_with_sample_user
        # log the staff member in
        client.force_login(greenweb_staff_user)

        user_admin_url = urls.reverse(
            "greenweb_admin:accounts_user_change",
            args=[user.id],
        )

        user_payload_without_provider_allocated = {
            "username": user.username,
            "email": user.email,
            "is_active": "on",
            "is_staff": "on",
            # simulate sending the empty result for a cleared
            # hosting provider
            "hostingprovider": "",
            "groups": [group.id for group in user.groups.all()],
        }

        # make an update via a POST to clear the hosting provider
        resp = client.post(
            user_admin_url, user_payload_without_provider_allocated, follow=True
        )

        assert resp.status_code == 200

        # is the user no longer allocated to the provider?
        provider.refresh_from_db()
        assert provider.user_set.count() == 0

        # is the provider also no longer associated with the user?
        user.refresh_from_db()
        assert user.hostingprovider is None


class TestUserCreationAdmin:
    """
    Do the user creation forms work as expected,
    and account for any legacy fields we have from earlier
    versions of the platform?
    """

    def test_create_user_as_greenweb_staff(self, db, client, greenweb_staff_user):
        """
        Can a green web staff user sign in, and create a new user to
        associate with an existing provider of services?
        """

        provider_groups = auth_models.Group.objects.filter(
            name__in=["hostingprovider", "datacenter"]
        )

        # sign them in
        client.force_login(greenweb_staff_user)

        add_user_url = urls.reverse("greenweb_admin:accounts_user_add")
        resp = client.get(add_user_url)

        # can they access the create user page?
        assert resp.status_code == 200
        # view_in_browser(resp.content)

        # can they use the add_form to create a new user?
        new_user_data = {
            "username": "Made Up Name",
            "password": "notARealPassword!12345",
            "email": "foo@example.com",
            "is_active": "on",
            "is_staff": "on",
            "groups": [group.id for group in provider_groups],
        }

        create_resp = client.post(add_user_url, new_user_data, follow=True)
        # view_in_browser(create_resp.content)

        assert create_resp.status_code == 200

        created_user = ac_models.User.objects.get(email=new_user_data["email"])
        for group in created_user.groups.all():
            assert group in provider_groups


def test_provider_request_accessible_by_admin(
    db,
    greenweb_staff_user,
):
    pr = ProviderRequestFactory()

    pr_admin = ac_admin.ProviderRequest(pr.__class__, admin_site.greenweb_admin)
    request = MagicMock()
    request.user = greenweb_staff_user

    inline_instances = pr_admin.get_inline_instances(request, pr)
    assert len(inline_instances) == 5

    assert pr_admin.has_add_permission(request)
    assert pr_admin.has_view_permission(request)
    assert pr_admin.has_change_permission(request)

    assert pr_admin.has_delete_permission(request) is False


def test_provider_request_not_accessible_by_regular_user(db, sample_hoster_user):
    pr = ProviderRequestFactory()

    pr_admin = ac_admin.ProviderRequest(pr.__class__, admin_site.greenweb_admin)
    request = MagicMock()
    request.user = sample_hoster_user

    inline_instances = pr_admin.get_inline_instances(request, pr)
    assert len(inline_instances) == 0

    assert pr_admin.has_add_permission(request) is False
    assert pr_admin.has_view_permission(request) is False
    assert pr_admin.has_change_permission(request) is False
    assert pr_admin.has_delete_permission(request) is False


def test_checkurl_form():
    """
    Check that passing in an url to our form
    returns a validated url.
    """

    form = admin_site.CheckUrlForm({"url": "https://google.com"})

    assert form.is_valid()
    assert form.cleaned_data["url"] == "google.com"


def test_extended_lookup_green_domain(
    db, mocker, green_ip_factory, green_domain_factory, rdap_content
):
    domain = "google.com"
    GOOGLE_COM_IP = "172.217.168.238"

    green_ip = green_ip_factory.create(ip_start=GOOGLE_COM_IP)
    green_domain = green_domain_factory.create(url=domain)
    green_provider = Hostingprovider.objects.get(pk=green_domain.hosted_by_id)

    # for readability
    green_provider.name = "Google"
    green_domain.hosted_by = "Google"
    green_domain.hosted_by_website = "google.com"
    green_ip.hostingprovider = green_provider

    green_ip.save()
    green_provider.save()
    green_domain.save()

    mocker.patch(
        "apps.greencheck.domain_check.GreenDomainChecker.convert_domain_to_ip",
        return_value=GOOGLE_COM_IP,
    )

    setup_domains(["google.com"], green_provider, green_ip)

    result = checker.extended_domain_info_lookup(domain)

    assert result["domain"] == domain

    # do we have a GreenDomain object?
    green_domain_lookup = result["green_domain"]
    # do we have our SiteCheck?
    site_check_lookup = result["site_check"]

    # do we have an rdap lookup object?
    rdap_lookup = result["whois_info"]
    assert rdap_lookup

    # do we have access our site check and green domain objects?
    assert green_domain_lookup.green is True
    assert site_check_lookup.green is True

    # does it look like it's querying the same object?
    assert rdap_content["query"] == GOOGLE_COM_IP
    # can we see the IP range?
    assert rdap_content["asn_cidr"] == "172.217.0.0/16"
    # can we see the AS number and the owner?
    assert rdap_content["asn_description"] == "GOOGLE, US"
    assert rdap_content["asn"] == "15169"
