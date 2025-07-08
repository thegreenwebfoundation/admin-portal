import pytest
from apps.greencheck import choices, models
from django.core import exceptions


@pytest.fixture
def green_ip_range_approval_request(green_ip):
    """
    Return an IP Range approval request, using the data from the provided
     green_ip fixture
    """
    return models.GreencheckIpApprove(
        action=choices.ActionChoice.NEW,
        status=choices.ActionChoice.NEW,
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
        action=choices.ActionChoice.NEW,
        status=choices.ActionChoice.NEW,
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
            ip_end="127.0.0.2",
            hostingprovider=hosting_provider,
        )
        gcip.save()

    @pytest.mark.parametrize(
        "ip_start, ip_end, range_length",
        [
            ("127.0.0.1", "127.0.0.1", 1),
            ("127.0.0.1", "127.0.0.255", 255),
            ("127.0.0.1", "127.0.1.1", 257),
        ],
    )
    def test_greencheck_ip_calculates_range(
        self, hosting_provider, db, ip_start, ip_end, range_length
    ):
        hosting_provider.save()
        gcip = models.GreencheckIp.objects.create(
            active=True,
            ip_start=ip_start,
            ip_end=ip_end,
            hostingprovider=hosting_provider,
        )
        assert gcip.ip_range_length() == range_length

    def test_greencheck_ip_range_validation(self, hosting_provider, db):
        hosting_provider.save()
        # given: invalid IP range (ip_start after ip_end)
        greencheck_ip = models.GreencheckIp.objects.create(
            active=True,
            ip_start="127.0.0.2",
            ip_end="127.0.0.1",
            hostingprovider=hosting_provider,
        )
        # when validating the object, ValidationError is raised
        with pytest.raises(exceptions.ValidationError):
            greencheck_ip.full_clean()


class TestGreencheckIPApproval:
    def test_process_approval_creates_greencheck_ip(
        self, db, green_ip_range_approval_request
    ):
        """
        Check that we can create a greencheck from the submitted request
        """

        green_ip = green_ip_range_approval_request.process_approval(
            choices.StatusApproval.APPROVED
        )

        assert green_ip_range_approval_request.greencheck_ip == green_ip


class TestGreencheckASNApproval:
    def test_process_approval_creates_greencheck_asn(
        self, db, green_asn_approval_request
    ):
        """
        Check that we can create a greencheck from the submitted request
        """

        green_asn = green_asn_approval_request.process_approval(
            choices.StatusApproval.APPROVED
        )

        assert green_asn_approval_request.greencheck_asn == green_asn


class TestHostingProviderASNApprovalNeedsReview:
    """
    We want to know when a hosting provider has an outstanding ASN that needs review.
    """

    @pytest.mark.parametrize(
        "action,status",
        [
            (choices.ActionChoice.NEW, choices.StatusApproval.NEW),
            (choices.ActionChoice.UPDATE, choices.StatusApproval.UPDATE),
            (choices.ActionChoice.NEW, choices.StatusApproval.UPDATE),
            (choices.ActionChoice.UPDATE, choices.StatusApproval.NEW),
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
            (choices.ActionChoice.NEW, choices.StatusApproval.NEW),
            (choices.ActionChoice.UPDATE, choices.StatusApproval.UPDATE),
            (choices.ActionChoice.NEW, choices.StatusApproval.UPDATE),
            (choices.ActionChoice.UPDATE, choices.StatusApproval.NEW),
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
            (choices.ActionChoice.NEW, choices.StatusApproval.NEW),
            (choices.ActionChoice.UPDATE, choices.StatusApproval.UPDATE),
            (choices.ActionChoice.NEW, choices.StatusApproval.UPDATE),
            (choices.ActionChoice.UPDATE, choices.StatusApproval.NEW),
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
            (choices.ActionChoice.NEW, choices.StatusApproval.NEW),
            (choices.ActionChoice.UPDATE, choices.StatusApproval.UPDATE),
            (choices.ActionChoice.NEW, choices.StatusApproval.UPDATE),
            (choices.ActionChoice.UPDATE, choices.StatusApproval.NEW),
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
            (choices.ActionChoice.NEW, choices.StatusApproval.NEW),
            (choices.ActionChoice.UPDATE, choices.StatusApproval.UPDATE),
            (choices.ActionChoice.NEW, choices.StatusApproval.UPDATE),
            (choices.ActionChoice.UPDATE, choices.StatusApproval.NEW),
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
            (choices.ActionChoice.NEW, choices.StatusApproval.NEW),
            (choices.ActionChoice.UPDATE, choices.StatusApproval.UPDATE),
            (choices.ActionChoice.NEW, choices.StatusApproval.UPDATE),
            (choices.ActionChoice.UPDATE, choices.StatusApproval.NEW),
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

class TestGreenDomainCreation:
    @pytest.mark.django_db
    def test_create_for_provider(self, db, hosting_provider_factory):
        #GIVEN a provider and a url
        provider = hosting_provider_factory.create()
        url = "example.com"

        #WHEN we create a greendomain for the given url and provider
        green_domain = models.GreenDomain.create_for_provider(url, provider)

        #THEN the corrrect properties of the provider are cached on the greendomain
        assert green_domain.hosted_by == provider.name
        assert green_domain.hosted_by_id == provider.id
        assert green_domain.hosted_by_website == provider.website
        assert green_domain.listed_provider == provider.is_listed

    def test_grey_result(self):
        #GIVEN  a url
        url = "example.com"

        #WHEN we create a greendomain for the given url as a grey result
        green_domain = models.GreenDomain.grey_result(url)

        #THEN the hosted_by properties are set to sensible defaults
        assert green_domain.hosted_by == None
        assert green_domain.hosted_by_id == None
        assert green_domain.hosted_by_website == None
        assert green_domain.listed_provider == False

    @pytest.mark.django_db
    def test_add_from_sitecheck(self, db, hosting_provider_factory):
        #GIVEN a provider and a sitecheck
        provider = hosting_provider_factory.create()
        provider.save()
        sitecheck = models.SiteCheck(
            url="https://example.com",
            ip="192.168.1.1",
            data=True,
            green=True,
            hosting_provider_id=provider.id,
            checked_at="2021-02-01T20:00:00Z",
            match_type="ip",
            match_ip_range="192.168.1.1/24",
            cached=True
        )

        #WHEN we create a greendomain for the given url as a grey result
        green_domain = models.GreenDomain.from_sitecheck(sitecheck)

        #THEN the corrrect properties of the provider are cached on the greendomain
        assert green_domain.hosted_by == provider.name
        assert green_domain.hosted_by_id == provider.id
        assert green_domain.hosted_by_website == provider.website
        assert green_domain.listed_provider == provider.is_listed

