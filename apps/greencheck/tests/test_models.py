import pytest

import ipaddress

from apps.greencheck import models
from apps.greencheck import forms
from apps.greencheck import choices


@pytest.fixture
def green_ip_range_approval_request(green_ip):
    return models.GreencheckIpApprove(
        action=choices.ActionChoice.new,
        status=choices.ActionChoice.new,
        hostingprovider=green_ip.hostingprovider,
        ip_end=green_ip.ip_end,
        ip_start=green_ip.ip_start,
    )


@pytest.fixture
def green_asn_approval_request(hosting_provider_with_sample_user):
    hosting_provider = hosting_provider_with_sample_user
    return models.GreencheckASNapprove(
        action=choices.ActionChoice.new,
        status=choices.ActionChoice.new,
        hostingprovider=hosting_provider,
        asn=12345,
    )


class TestGreenCheckIP:
    def test_greencheckip_has_start_and_end(self, hosting_provider, db):
        hosting_provider.save()
        gcip = models.GreencheckIp.objects.create(
            active=True,
            ip_start="127.0.0.1",
            ip_end="120.0.0.1",
            hostingprovider=hosting_provider,
        )
        gcip.save()


class TestHostingProviderASNApprovalNeedsReview:
    """
    We want to know when a hosting provider has an outstanding ASN that needs review.
    """

    def test_hosting_provider_is_pending_with_new_ASN(
        self, db, hosting_provider_with_sample_user, green_asn_approval_request
    ):
        """
        When a hosting provider has a ASN approval waiting a response,
        a hosting provider should count as in a 'needs review' state.
        """

        # when we pass nothing in we expect a false response
        assert not hosting_provider_with_sample_user.needs_review()

        # we call this with the new request before persisting it
        # to database. this simulates its use in forms or serailisers
        assert hosting_provider_with_sample_user.needs_review(
            green_asn_approval_request
        )

        # once a request has been persisted, we still want future `needs_review
        # checks to count as True.
        green_asn_approval_request.save()
        assert hosting_provider_with_sample_user.needs_review()

    def test_hosting_provider_is_pending_with_new_IRange(
        self, db, hosting_provider_with_sample_user, green_ip_range_approval_request
    ):

        # when we pass nothing in we expect a false response
        assert not hosting_provider_with_sample_user.needs_review()

        # we call this with the new request before persisting it
        # to database. this simulates its use in forms or serailisers
        assert hosting_provider_with_sample_user.needs_review(
            green_ip_range_approval_request
        )

        # once a request has been persisted, we still want future `needs_review
        # checks to count as True.
        green_ip_range_approval_request.save()
        assert hosting_provider_with_sample_user.needs_review()


class TestHostingProviderSendsNotification:
    def test_hosting_provider_notifications_sent_when_review_needed_for_asn(
        self,
        db,
        hosting_provider_with_sample_user,
        green_asn_approval_request,
        mailoutbox,
    ):
        """
        When a hosting provider counts as in need of review, we only want to send an
        email if we are tranisitioning from a state of having no claims to
        review to having claims to review.
        We do this, because we don't want to deluge admins with unnecessary
        notifications.
        """

        assert not hosting_provider_with_sample_user.needs_review()

        hosting_provider_with_sample_user.mark_as_pending_review(
            green_asn_approval_request
        )

        assert len(mailoutbox) == 1

        msg, *_ = mailoutbox
        assert hosting_provider_with_sample_user.name in msg.subject

    def test_hosting_provider_notifications_sent_when_review_needed_for_ip_range(
        self,
        db,
        hosting_provider_with_sample_user,
        green_ip_range_approval_request,
        mailoutbox,
    ):
        """
        As above, but with an IP Range. We can't pass fixtures in as parameters in tests
        """

        assert not hosting_provider_with_sample_user.needs_review()

        hosting_provider_with_sample_user.mark_as_pending_review(
            green_ip_range_approval_request
        )

        assert len(mailoutbox) == 1

        msg, *_ = mailoutbox
        assert hosting_provider_with_sample_user.name in msg.subject

    def test_hosting_provider_does_not_send_duplicate_notifications_for_asn(
        self,
        db,
        hosting_provider_with_sample_user,
        green_asn_approval_request,
        mailoutbox,
    ):
        """
            When a hosting provider counts as in need of review, we only want to send
            an email if we are tranisitioning from a state of having no claims
            to review, to a state of having claims to review.
            We do this because we don't want to deluge admins with unnecessary
            notifications.
            """

        assert not hosting_provider_with_sample_user.needs_review()

        hosting_provider_with_sample_user.mark_as_pending_review(
            green_asn_approval_request
        )

        # after a successful API or form submission, we save the approval request
        # so save it here to represent it
        green_asn_approval_request.save()

        # call this again, to simulate multiple claims being made
        hosting_provider_with_sample_user.mark_as_pending_review(
            green_asn_approval_request
        )

        assert len(mailoutbox) == 1

        msg, *_ = mailoutbox
        assert hosting_provider_with_sample_user.name in msg.subject

    def test_hosting_provider_does_not_send_duplicate_notifications_for_ip_range(
        self,
        db,
        hosting_provider_with_sample_user,
        green_ip_range_approval_request,
        mailoutbox,
    ):
        """
            When a hosting provider counts as in need of review, we only want to send
            an email if we are tranisitioning from a state of having no claims
            to review, to a state of having claims to review.
            We do this because we don't want to deluge admins with unnecessary
            notifications.
            """

        assert not hosting_provider_with_sample_user.needs_review()

        hosting_provider_with_sample_user.mark_as_pending_review(
            green_ip_range_approval_request
        )

        # after a successful API or form submission, we save the approval request
        # so save it here to represent it
        green_ip_range_approval_request.save()

        # call this again, to simulate multiple claims being made
        hosting_provider_with_sample_user.mark_as_pending_review(
            green_ip_range_approval_request
        )

        assert len(mailoutbox) == 1

        msg, *_ = mailoutbox
        assert hosting_provider_with_sample_user.name in msg.subject

