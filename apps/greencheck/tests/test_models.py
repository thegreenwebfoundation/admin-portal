import pytest
from apps.greencheck import choices, models


@pytest.fixture
def green_ip_range_approval_request(green_ip):
    """
    Return an IP Range approval request, using the data from the provided
     green_ip fixture
    """
    return models.GreencheckIpApprove(
        action=choices.ActionChoice.new,
        status=choices.ActionChoice.new,
        hostingprovider=green_ip.hostingprovider,
        ip_end=green_ip.ip_end,
        ip_start=green_ip.ip_start,
    )


@pytest.fixture
def green_asn_approval_request(hosting_provider_with_sample_user):
    """
    Return an ASN approval request for the given hosting provider
    """
    hosting_provider = hosting_provider_with_sample_user
    return models.GreencheckASNapprove(
        action=choices.ActionChoice.new,
        status=choices.ActionChoice.new,
        hostingprovider=hosting_provider,
        asn=12345,
    )


class TestGreenCheckIP:
    def test_greencheckip_has_start_and_end(self, hosting_provider, db):
        """
        Check that our IP range requests can be saved succesfully.
        We rely on a custom IP addressfield, so this works as a check
        to see if's converting to a form we can persiste in the database
        """
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

    @pytest.mark.parametrize(
        "action,status",
        [
            (choices.ActionChoice.new, choices.StatusApproval.new),
            (choices.ActionChoice.update, choices.StatusApproval.update),
            (choices.ActionChoice.new, choices.StatusApproval.update),
            (choices.ActionChoice.update, choices.StatusApproval.new),
        ],
    )
    def test_hosting_provider_is_pending_with_new_ASN(
        self,
        db,
        hosting_provider_with_sample_user,
        green_asn_approval_request,
        status,
        action,
    ):
        """
        When a hosting provider has a ASN approval request created, we should
        be able to mark the provider as 'pending review', but a provider has
        outstanding approval requests, we should be able to tell if notification
        would have been sent.

        """
        green_asn_approval_request.status = status
        green_asn_approval_request.action = action

        # when we pass nothing in we expect a false response
        assert not hosting_provider_with_sample_user.outstanding_approval_requests()

        # we call this with the new request before persisting it
        # to database. this simulates its use in forms or serializers
        assert hosting_provider_with_sample_user.mark_as_pending_review(
            green_asn_approval_request
        )

        # once a request has been persisted, we still want to be able to see if
        # there are outstanding_approval_requests, even if we are no longer sending
        # more notifications
        green_asn_approval_request.save()
        assert hosting_provider_with_sample_user.outstanding_approval_requests()
        assert not hosting_provider_with_sample_user.mark_as_pending_review(
            green_asn_approval_request
        )

    @pytest.mark.parametrize(
        "action,status",
        [
            (choices.ActionChoice.new, choices.StatusApproval.new),
            (choices.ActionChoice.update, choices.StatusApproval.update),
            (choices.ActionChoice.new, choices.StatusApproval.update),
            (choices.ActionChoice.update, choices.StatusApproval.new),
        ],
    )
    def test_hosting_provider_is_pending_with_new_ip_range(
        self,
        db,
        hosting_provider_with_sample_user,
        green_ip_range_approval_request,
        status,
        action,
    ):
        """
        Similar in intention as `test_hosting_provider_is_pending_with_new_ASN`,
         but for IP range approval requests.
        """

        green_ip_range_approval_request.status = status
        green_ip_range_approval_request.action = action

        # when we pass nothing in we expect a false response
        assert not hosting_provider_with_sample_user.outstanding_approval_requests()

        # we call this with the new request before persisting it
        # to database. this simulates its use in forms or serializers
        assert hosting_provider_with_sample_user.mark_as_pending_review(
            green_ip_range_approval_request
        )
        # once a request has been persisted, we still want to be able to see if
        # there are outstanding_approval_requests, even if we are no longer sending
        # more notifications
        green_ip_range_approval_request.save()
        assert hosting_provider_with_sample_user.outstanding_approval_requests()
        assert not hosting_provider_with_sample_user.mark_as_pending_review(
            green_ip_range_approval_request
        )


class TestHostingProviderSendsNotification:
    @pytest.mark.parametrize(
        "action,status",
        [
            (choices.ActionChoice.new, choices.StatusApproval.new),
            (choices.ActionChoice.update, choices.StatusApproval.update),
            (choices.ActionChoice.new, choices.StatusApproval.update),
            (choices.ActionChoice.update, choices.StatusApproval.new),
        ],
    )
    def test_hosting_provider_notifications_sent_when_review_needed_for_asn(
        self,
        db,
        hosting_provider_with_sample_user,
        green_asn_approval_request,
        mailoutbox,
        status,
        action,
    ):
        """
        When a hosting provider counts as in need of review, we want to send an
        email if we are tranisitioning from a state of having no claims to
        review to having claims to review.
        """
        green_asn_approval_request.status = status
        green_asn_approval_request.action = action

        assert not hosting_provider_with_sample_user.outstanding_approval_requests()

        hosting_provider_with_sample_user.mark_as_pending_review(
            green_asn_approval_request
        )

        assert len(mailoutbox) == 1

        msg, *_ = mailoutbox
        assert hosting_provider_with_sample_user.name in msg.subject

    @pytest.mark.parametrize(
        "action,status",
        [
            (choices.ActionChoice.new, choices.StatusApproval.new),
            (choices.ActionChoice.update, choices.StatusApproval.update),
            (choices.ActionChoice.new, choices.StatusApproval.update),
            (choices.ActionChoice.update, choices.StatusApproval.new),
        ],
    )
    def test_hosting_provider_notifications_sent_when_review_needed_for_ip_range(
        self,
        db,
        hosting_provider_with_sample_user,
        green_ip_range_approval_request,
        mailoutbox,
        status,
        action,
    ):
        """
        Similar to `test_hosting_provider_notifications_sent_when_review_needed_for_asn`
        but with an IP Range approval request.
        """
        green_ip_range_approval_request.status = status
        green_ip_range_approval_request.action = action

        assert not hosting_provider_with_sample_user.outstanding_approval_requests()

        hosting_provider_with_sample_user.mark_as_pending_review(
            green_ip_range_approval_request
        )

        assert len(mailoutbox) == 1

        msg, *_ = mailoutbox
        assert hosting_provider_with_sample_user.name in msg.subject

    @pytest.mark.parametrize(
        "action,status",
        [
            (choices.ActionChoice.new, choices.StatusApproval.new),
            (choices.ActionChoice.update, choices.StatusApproval.update),
            (choices.ActionChoice.new, choices.StatusApproval.update),
            (choices.ActionChoice.update, choices.StatusApproval.new),
        ],
    )
    def test_hosting_provider_does_not_send_duplicate_notifications_for_asn(
        self,
        db,
        hosting_provider_with_sample_user,
        green_asn_approval_request,
        mailoutbox,
        status,
        action,
    ):
        """
        When a hosting provider counts as in need of review, we only want to send
        an email if we are tranisitioning from a state of having no claims
        to review, to a state of having claims to review.
        We do this because we don't want to deluge admins with unnecessary
        notifications.
        """
        green_asn_approval_request.status = status
        green_asn_approval_request.action = action

        assert not hosting_provider_with_sample_user.outstanding_approval_requests()

        hosting_provider_with_sample_user.mark_as_pending_review(
            green_asn_approval_request
        )

        # after a successful API or form submission, we save the approval request
        # calling save here simulated the same behaviour
        green_asn_approval_request.save()

        # call this again, to simulate multiple claims being made
        hosting_provider_with_sample_user.mark_as_pending_review(
            green_asn_approval_request
        )

        assert len(mailoutbox) == 1

        msg, *_ = mailoutbox
        assert hosting_provider_with_sample_user.name in msg.subject

    @pytest.mark.parametrize(
        "action,status",
        [
            (choices.ActionChoice.new, choices.StatusApproval.new),
            (choices.ActionChoice.update, choices.StatusApproval.update),
            (choices.ActionChoice.new, choices.StatusApproval.update),
            (choices.ActionChoice.update, choices.StatusApproval.new),
        ],
    )
    def test_hosting_provider_does_not_send_duplicate_notifications_for_ip_range(
        self,
        db,
        hosting_provider_with_sample_user,
        green_ip_range_approval_request,
        mailoutbox,
        action,
        status,
    ):
        """
        Similar to `test_hosting_provider_does_not_send_duplicate_notifications_for_asn`
        above, but for IP Ranges instead.
        """

        green_ip_range_approval_request.status = status
        green_ip_range_approval_request.action = action
        assert not hosting_provider_with_sample_user.outstanding_approval_requests()

        hosting_provider_with_sample_user.mark_as_pending_review(
            green_ip_range_approval_request
        )

        # after a successful API or form submission, we save the approval request
        # calling save here simulated the same behaviour
        green_ip_range_approval_request.save()

        # call this again, to simulate multiple claims being made
        hosting_provider_with_sample_user.mark_as_pending_review(
            green_ip_range_approval_request
        )

        assert len(mailoutbox) == 1

        msg, *_ = mailoutbox
        assert hosting_provider_with_sample_user.name in msg.subject
