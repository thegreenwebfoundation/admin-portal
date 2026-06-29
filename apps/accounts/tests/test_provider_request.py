import io
import logging
import random
from datetime import date, datetime
from ipaddress import ip_address

import pytest
from django import urls
from django.conf import settings
from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.test import RequestFactory
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.urls import reverse
from faker import Faker
from freezegun import freeze_time
from waffle.testutils import override_flag

from apps.accounts import admin as ac_admin
from apps.accounts import admin_site
from apps.accounts import forms as account_forms
from apps.accounts.factories import (
    ProviderRequestASNFactory,
    ProviderRequestEvidenceFactory,
    ProviderRequestFactory,
    ProviderRequestIPRangeFactory,
    ProviderRequestLocationFactory,
    SupportingEvidenceFactory,
    VerificationBasisFactory,
)
from apps.greencheck.factories import (
    GreenASNFactory,
    GreenIpFactory,
    ServiceFactory,
    UserFactory,
)

from .. import models, views

faker = Faker()


logger = logging.getLogger(__name__)  # noqa


@pytest.fixture()
def wizard_form_org_details_data():
    """
    Returns valid data for step ORG_DETAILS of the wizard
    as expected by the POST request.
    """
    return {
        "provider_request_wizard_view-current_step": "0",
        "0-name": " ".join(faker.words(5)),
        "0-website": faker.url(),
        "0-description": faker.sentence(10),
        "0-authorised_by_org": "True",
    }


@pytest.fixture()
def wizard_form_org_location_data():
    """
    Returns valid data for the step ORG_LOCATIONS of the wizard,
    as expected by the POST request.
    """
    return {
        "provider_request_wizard_view-current_step": "1",
        "locations__1-TOTAL_FORMS": "3",
        "locations__1-INITIAL_FORMS": "0",
        "locations__1-0-country": faker.country_code(),
        "locations__1-0-city": faker.city(),
        "locations__1-1-country": faker.country_code(),
        "locations__1-1-city": faker.city(),
        "locations__1-2-country": faker.country_code(),
        "locations__1-2-city": faker.city(),
        "extra__1-location_import_required": "True",
    }


@pytest.fixture()
def wizard_form_services_data():
    """
    Returns valid data for step SERVICES of the wizard
    as expected by the POST request.
    """
    for _ in range(5):
        ServiceFactory.create()

    tags_choices = models.Service.objects.all()
    services_sample = random.sample([tag.slug for tag in tags_choices], 3)

    return {
        "provider_request_wizard_view-current_step": "2",
        "2-services": services_sample,
    }


@pytest.fixture()
def wizard_form_verification_bases_data():
    """
    Returns valid data for step BASIS FOR VERIFICATION of the wizard as expected by the POST request.
    """
    for _ in range(5):
        VerificationBasisFactory.create()

    # draw from the active version's choices (June 2026 when the v2 flag is off)
    # so the submitted slugs are always valid for the rendered form
    choices = models.ProviderRequest.get_verification_bases_choices()
    bases_sample = random.sample([slug for slug, _label in choices], 3)

    return {
        "provider_request_wizard_view-current_step": "3",
        "3-verification_bases": bases_sample,
    }


@pytest.fixture()
def wizard_form_verification_bases_with_linked_provider_data():
    """
    Returns valid data for step BASIS FOR VERIFICATION including a linked provider.
    """
    for _ in range(5):
        VerificationBasisFactory.create()

    # ensure the reseller basis exists and is included
    reseller_slug = "we-resell-or-actively-use-a-provider-that-is-already-in-the-green-web-dataset"
    reseller_basis, _ = models.VerificationBasis.objects.get_or_create(
        slug=reseller_slug,
        defaults={"name": "We resell or actively use a provider that is already in the Green Web Dataset."},
    )

    # draw from the active version's choices (June 2026 when the v2 flag is off)
    choices = models.ProviderRequest.get_verification_bases_choices()
    choice_slugs = [slug for slug, _label in choices]
    bases_sample = random.sample(choice_slugs, min(2, len(choice_slugs)))
    bases_sample.append(reseller_basis.slug)

    upstream = models.Hostingprovider.objects.create(
        name="Upstream Green Provider",
        country="GB",
        archived=False,
        is_listed=True,
        website="https://example.com",
    )

    return {
        "provider_request_wizard_view-current_step": "3",
        "3-verification_bases": bases_sample,
        "3-upstream_providers": [str(upstream.id)],
    }

@pytest.fixture()
def wizard_form_evidence_data(fake_evidence):
    """
    Returns valid data for step GREEN_EVIDENCE of the wizard
    as expected by the POST request.
    """
    return {
        "provider_request_wizard_view-current_step": "4",
        "4-TOTAL_FORMS": 2,
        "4-INITIAL_FORMS": 0,
        "4-0-title": " ".join(faker.words(3)),
        "4-0-link": faker.url(),
        "4-0-file": "",
        "4-0-type": models.EvidenceType.WEB_PAGE.value,
        "4-0-public": "on",
        "4-1-title": " ".join(faker.words(3)),
        "4-1-link": "",
        "4-1-file": fake_evidence,
        "4-1-type": models.EvidenceType.ANNUAL_REPORT.value,
        "4-1-public": "on",
    }


@pytest.fixture()
def sorted_ips():
    """
    Returns a list of fake IPv4 addresses, sorted in ascending order
    """
    return sorted([faker.ipv4() for _ in range(10)], key=lambda x: ip_address(x))


@pytest.fixture()
def wizard_form_network_data(sorted_ips):
    """
    Returns valid data for step NETWORK_FOOTPRINT of the wizard
    as expected by the POST request.
    """
    return {
        "provider_request_wizard_view-current_step": "5",
        "ips__5-TOTAL_FORMS": "2",
        "ips__5-INITIAL_FORMS": "0",
        "ips__5-0-start": sorted_ips[0],
        "ips__5-0-end": sorted_ips[1],
        "ips__5-1-start": sorted_ips[2],
        "ips__5-1-end": sorted_ips[3],
        "asns__5-TOTAL_FORMS": "1",
        "asns__5-INITIAL_FORMS": "0",
        "asns__5-0-asn": faker.random_int(min=100, max=999),
    }


@pytest.fixture()
def wizard_form_network_explanation_only():
    """
    Returns valid explanation for step NETWORK_FOOTPRINT of the
    form wizard, without any IP or AS information.
    """
    return {
        "provider_request_wizard_view-current_step": "5",
        "ips__5-TOTAL_FORMS": "0",
        "ips__5-INITIAL_FORMS": "0",
        "asns__5-TOTAL_FORMS": "0",
        "asns__5-INITIAL_FORMS": "0",
        "extra__5-missing_network_explanation": faker.sentence(10),
    }


@pytest.fixture()
def wizard_form_consent():
    """
    Returns valid data for step CONSENT of the wizard,
    as expected by the POST request.
    """
    return {
        "provider_request_wizard_view-current_step": "6",
        "6-data_processing_opt_in": "on",
        "6-newsletter_opt_in": "off",
    }


@pytest.fixture()
def wizard_form_preview():
    """
    Returns valid data for step PREVIEW of the wizard,
    as expected by the POST request.
    """
    return {
        "provider_request_wizard_view-current_step": "7",
    }


@pytest.fixture()
def fake_evidence():
    """
    Returns a file-like object with fake content
    """
    file = io.BytesIO(faker.text().encode())
    file.name = faker.file_name()
    return file


@pytest.mark.django_db
@pytest.mark.parametrize(
    "evidence_data",
    [
        {
            "title": "this one has both: link and a file",
            "link": "www.example.com",
            "file": File(file=io.BytesIO(faker.text().encode()), name=faker.file_name()),
            "type": models.EvidenceType.CERTIFICATE,
        },
        {
            "title": "this one has neither link nor file",
            "type": models.EvidenceType.CERTIFICATE,
        },
    ],
    ids=["both_file_and_link", "neither_file_nor_link"],
)
def test_evidence_validation_fails(evidence_data):

    evidence_data["request"] = ProviderRequestFactory.create()

    evidence = models.ProviderRequestEvidence.objects.create(**evidence_data)

    with pytest.raises(ValidationError):
        evidence.full_clean()


@pytest.mark.django_db
def test_regular_user_cannot_access_admin(user, client):
    client.force_login(user)
    admin_url = urls.reverse("greenweb_admin:accounts_providerrequest_changelist")

    response = client.get(admin_url)

    assert response.status_code == 403


@pytest.mark.django_db
def test_staff_can_access_admin(greenweb_staff_user, client):
    client.force_login(greenweb_staff_user)
    admin_url = urls.reverse("greenweb_admin:accounts_providerrequest_changelist")

    response = client.get(admin_url)

    assert response.status_code == 200


@pytest.mark.django_db
def test_detail_view_accessible_by_creator(client):
    # given: provider request exists
    pr = ProviderRequestFactory.create()

    # when: accessing its detail view by the creator
    client.force_login(pr.created_by)
    response = client.get(urls.reverse("provider_request_detail", args=[str(pr.id)]))

    # then: page for the correct provider request is rendered
    assert response.status_code == 200
    assert response.context_data["providerrequest"] == pr


@pytest.mark.django_db
def test_detail_view_accessible_by_admin(client, greenweb_staff_user):
    # given: provider request exists
    pr = ProviderRequestFactory.create()

    # when: accessing its detail view by greenweb_staff_user
    client.force_login(greenweb_staff_user)
    response = client.get(urls.reverse("provider_request_detail", args=[str(pr.id)]))

    # then: page for the correct provider request is rendered
    assert response.status_code == 200
    assert response.context_data["providerrequest"] == pr


@pytest.mark.django_db
def test_detail_view_forbidden_for_others(client, user):
    # given: provider request exists
    pr = ProviderRequestFactory.create()

    # when: accessing its detail view by another user
    client.force_login(user)
    response = client.get(urls.reverse("provider_request_detail", args=[str(pr.id)]))

    # then: page is not accessible
    assert response.status_code == 404


@pytest.mark.django_db
def test_wizard_view_happy_path(
    user,
    client,
    wizard_form_org_details_data,
    wizard_form_org_location_data,
    wizard_form_services_data,
    wizard_form_verification_bases_data,
    wizard_form_evidence_data,
    wizard_form_network_data,
    wizard_form_consent,
    wizard_form_preview,
):
    # given: valid form data and authenticated user
    form_data = [
        wizard_form_org_details_data,
        wizard_form_org_location_data,
        wizard_form_services_data,
        wizard_form_verification_bases_data,
        wizard_form_evidence_data,
        wizard_form_network_data,
        wizard_form_consent,
        wizard_form_preview,
    ]
    client.force_login(user)

    # when: submitting form data for consecutive wizard steps
    for step, data in enumerate(form_data, 1):
        response = client.post(urls.reverse("provider_registration"), data, follow=True)
        # then: for all steps except the last one,
        # next wizard step is rendered upon submitting the data
        if step < len(form_data):
            assert response.context_data["wizard"]["steps"].current == str(step)
        assert response.status_code == 200

    # then: submitting the final step redirects to the detail view
    assert response.resolver_match.func.view_class is views.ProviderRequestDetailView

    # then: a ProviderRequest object exists in the db
    pr = response.context_data["providerrequest"]
    assert models.ProviderRequest.objects.filter(id=pr.id).exists()

    # then: the status is set to PENDING_REVIEW
    created_pr = models.ProviderRequest.objects.get(id=pr.id)
    assert created_pr.status == models.ProviderRequestStatus.PENDING_REVIEW

    # and: we have logged the creation in the history for this provider request
    # to give us an audit trail
    log_message = LogEntry.objects.get(object_id=created_pr.id)

    assert log_message.user == user
    assert log_message.action_flag == ADDITION
    assert ContentType.objects.get_for_model(pr).pk == log_message.content_type_id
    assert log_message.change_message == "Provider request created for review"


def _create_provider_request(client, form_data) -> HttpResponse:
    """
    Run through the steps the form wizard with the provided form data,
    to create a new provider request.
    """
    response = None
    for step, data in enumerate(form_data, 1):
        response = client.post(urls.reverse("provider_registration"), data, follow=True)
    return response


@pytest.mark.django_db
def test_wizard_sends_email_on_submission(
    user,
    client,
    wizard_form_org_details_data,
    wizard_form_org_location_data,
    wizard_form_services_data,
    wizard_form_verification_bases_data,
    wizard_form_evidence_data,
    wizard_form_network_data,
    wizard_form_consent,
    wizard_form_preview,
    mailoutbox,
):
    """
    Given: a working set of data
    When: a user has completed a form submission,
    Then: an email should have been sent to the user and internal staff
    """

    # given: valid form data and authenticated user
    form_data = [
        wizard_form_org_details_data,
        wizard_form_org_location_data,
        wizard_form_services_data,
        wizard_form_verification_bases_data,
        wizard_form_evidence_data,
        wizard_form_network_data,
        wizard_form_consent,
        wizard_form_preview,
    ]
    client.force_login(user)

    # when: a multi step submission has been successfully completed
    _create_provider_request(client, form_data)

    # then: we should see an email being sent
    assert len(mailoutbox) == 1
    eml = mailoutbox[0]

    msg_body_txt = eml.body
    msg_body_html = eml.alternatives[0][0]

    # then: and our email is addressed to the people we expect it to be
    assert user.email in eml.to
    assert "support@greenweb.org" in eml.cc

    # then: and our email has the subject and copy we were expecting
    assert "Your Green Web Dataset verification request:" in eml.subject

    assert "complete a Green Web Dataset verification request" in msg_body_txt
    assert "complete a Green Web Dataset verification request" in msg_body_html

    # then: and our email includes a BCC address so we can track status in
    # trello via sending a message to the email-to-board address
    assert settings.TRELLO_REGISTRATION_EMAIL_TO_BOARD_ADDRESS in eml.bcc

    # then: and finally our email links back to the submission, contains the status,
    # and the correct organisation
    provider_name = wizard_form_org_details_data["0-name"]
    provider_request = models.ProviderRequest.objects.get(name=provider_name)
    request_path = urls.reverse("provider_request_detail", args=[provider_request.id])

    link_to_verification_request = f"http://testserver{request_path}"

    assert provider_name in eml.subject
    assert link_to_verification_request in msg_body_txt
    assert link_to_verification_request in msg_body_html

    assert provider_request.name in msg_body_txt
    assert provider_request.name in msg_body_html


@pytest.mark.django_db
def test_approve_when_hostingprovider_for_user_exists(user_with_provider):
    # given: provider request submitted by a user that already has a Hostingprovider assigned
    pr = ProviderRequestFactory.create(created_by=user_with_provider)
    loc1 = ProviderRequestLocationFactory.create(request=pr)
    existing_provider = user_with_provider.hosting_providers.first()

    # then: approving the request succeeds
    new_provider = pr.approve()

    # then: user has access to 2 providers
    assert existing_provider in user_with_provider.hosting_providers
    assert new_provider in user_with_provider.hosting_providers


def test_approve_fails_when_hostingprovider_exists(db, hosting_provider):
    # given: Hostingprovider related to a given ProviderRequest already exists
    pr = ProviderRequestFactory.create()
    hosting_provider.request = pr
    hosting_provider.save()

    # then: approving the request fails
    with pytest.raises(ValueError):
        pr.approve()


def test_approve_fails_when_request_already_approved(db):
    # given: ProviderRequest is already approved
    pr = ProviderRequestFactory.create(status=models.ProviderRequestStatus.APPROVED)

    # then: approving the request fails
    with pytest.raises(ValueError):
        pr.approve()


@pytest.mark.django_db
def test_approve_first_location_is_persisted():
    # given: provider request with 2 locations
    pr = ProviderRequestFactory.create()
    loc1 = ProviderRequestLocationFactory.create(request=pr)
    loc2 = ProviderRequestLocationFactory.create(request=pr)

    # when: provider request is approved
    result = pr.approve()
    hp = models.Hostingprovider.objects.get(id=result.id)

    # then: first location is persisted
    assert hp.city == loc1.city
    assert hp.country == loc1.country


@pytest.mark.django_db
def test_approve_asn_already_exists(green_asn):
    # given: provider request with ASN that already exists
    green_asn.save()
    pr = ProviderRequestFactory.create()
    loc = ProviderRequestLocationFactory(request=pr)
    asn = ProviderRequestASNFactory(request=pr, asn=green_asn.asn)

    # then: provider request approval fails
    with pytest.raises(ValueError):
        pr.approve()

    # then: changes to Hostingprovider and User models are rolled back
    # GOTCHA: we retrieve the User from the database again
    #         because User model state (pr.created_by) is not reset by the rollback
    assert (
        models.User.objects.get(pk=pr.created_by.pk).hosting_providers.exists() is False
    )
    assert models.Hostingprovider.objects.filter(request=pr).exists() is False


@freeze_time("Apr 25th, 2023, 12:00:01")
@pytest.mark.django_db
def test_approve_changes_status_to_approved():
    # given: a provider request is created
    pr = ProviderRequestFactory.create()
    ProviderRequestLocationFactory.create(request=pr)
    ProviderRequestEvidenceFactory.create(request=pr)

    # when: the request is approved
    pr.approve()

    # when: we fetch the request from the database again
    result = models.ProviderRequest.objects.get(pk=pr.pk)

    # then: the request status is changed
    assert result.status == models.ProviderRequestStatus.APPROVED
    # then: the approval date is recorded
    assert result.approved_at == datetime(2023, 4, 25, 12, 0, 1)


@pytest.mark.django_db
def test_approve_creates_hosting_provider():
    # given: a provider request with services is created
    pr = ProviderRequestFactory.create(services=faker.words(nb=4), verification_bases=faker.words(nb=4))
    ProviderRequestLocationFactory.create(request=pr)
    ProviderRequestEvidenceFactory.create(request=pr)

    # when: the request is approved
    result = pr.approve()
    hp = models.Hostingprovider.objects.get(id=result.id)

    # then: resulting Hostingprovider is configured properly
    assert hp.name == pr.name
    assert hp.description == pr.description
    assert list(hp.services.all()) == list(pr.services.all())
    assert list(hp.verification_bases.all()) == list(pr.verification_bases.all())
    assert hp.website == pr.website
    assert hp.request == pr
    assert hp.created_by == pr.created_by
    # then: user who created the request has permissions to manage the new hosting provider
    assert hp in pr.created_by.hosting_providers

    # provider is visible by default
    # appropriate tag is added
    assert hp.is_listed is True
    assert "up-to-date" in hp.staff_labels.slugs()
    # "other-none" is the label condition check for
    # when someone is just trying to get a site marked
    # as green when they don't offer hosted services
    assert "other-none" not in hp.services.slugs()


@pytest.mark.django_db
def test_approve_updates_existing_provider(hosting_provider_with_sample_user):
    # given: a provider request linked to an existing hosting provider
    pr = ProviderRequestFactory.create(
        services=faker.words(nb=4), provider=hosting_provider_with_sample_user
    )
    ProviderRequestLocationFactory.create(request=pr)
    ProviderRequestEvidenceFactory.create(request=pr)

    # when: the request is approved
    result = pr.approve()
    hp = models.Hostingprovider.objects.get(id=result.id)

    # then: resulting Hostingprovider is the one linked to the original request
    assert hp.id == pr.provider.id

    # then: resulting Hostingprovider is configured properly
    assert hp.name == pr.name
    assert hp.description == pr.description
    assert set(hp.services.all()) == set(pr.services.all())
    assert hp.website == pr.website
    assert hp.request == pr
    assert hp.created_by == pr.created_by
    # then: user who created the request has permissions to manage the new hosting provider
    assert hp in pr.created_by.hosting_providers

    # provider is visible by default
    # appropriate tag is added
    assert hp.is_listed is True
    assert hp.archived is False
    assert "up-to-date" in hp.staff_labels.slugs()
    # "other-none" is the label condition check for
    # when someone is just trying to get a site marked
    # as green when they don't offer hosted services
    assert "other-none" not in hp.services.slugs()


@pytest.mark.django_db
def test_approve_creates_hosting_provider_with_upstream_providers():
    # given: a provider request with linked providers is created
    upstream = models.Hostingprovider.objects.create(
        name="Upstream Green",
        country="GB",
        archived=False,
        is_listed=True,
        website="https://upstream.example.com",
    )
    pr = ProviderRequestFactory.create(
        services=faker.words(nb=4), verification_bases=faker.words(nb=4)
    )
    pr.upstream_providers.set([upstream])
    ProviderRequestLocationFactory.create(request=pr)
    ProviderRequestEvidenceFactory.create(request=pr)

    # when: the request is approved
    result = pr.approve()
    hp = models.Hostingprovider.objects.get(id=result.id)

    # then: resulting Hostingprovider has the linked providers copied
    assert hp.upstream_providers.count() == 1
    assert upstream in hp.upstream_providers.all()


@pytest.mark.django_db
def test_approve_updates_existing_provider_with_upstream_providers(
    hosting_provider_with_sample_user,
):
    # given: an existing hosting provider and a new upstream provider
    upstream = models.Hostingprovider.objects.create(
        name="Upstream Green",
        country="GB",
        archived=False,
        is_listed=True,
        website="https://upstream.example.com",
    )
    pr = ProviderRequestFactory.create(
        services=faker.words(nb=4), provider=hosting_provider_with_sample_user
    )
    pr.upstream_providers.set([upstream])
    ProviderRequestLocationFactory.create(request=pr)
    ProviderRequestEvidenceFactory.create(request=pr)

    # when: the request is approved
    result = pr.approve()
    hp = models.Hostingprovider.objects.get(id=result.id)

    # then: the existing provider is updated with the new linked providers
    assert hp.id == pr.provider.id
    assert hp.upstream_providers.count() == 1
    assert upstream in hp.upstream_providers.all()


@pytest.mark.django_db
def test_approve_updates_existing_provider_without_deleting_asns(
    hosting_provider_with_sample_user,
):
    """
    Check that approving a provider request does not delete an existing ASN, but
    preserves the state instead.
    """
    # Given: an existing ASN linked to our provider
    original_asn = GreenASNFactory.create(
        hostingprovider=hosting_provider_with_sample_user
    )

    # and: a provider request linked to an existing hosting provider
    pr = ProviderRequestFactory.create(
        services=faker.words(nb=4), provider=hosting_provider_with_sample_user
    )

    ProviderRequestLocationFactory.create(request=pr)
    ProviderRequestEvidenceFactory.create(request=pr)
    ProviderRequestASNFactory.create(request=pr, asn=original_asn.asn)

    # when: the request is approved
    result = pr.approve()
    hp = models.Hostingprovider.objects.get(id=result.id)
    # we expect to only have one active ASN in our test, so we check then fetch it
    assert hp.greencheckasn_set.filter(active=True).count() == 1
    post_approval_asn = hp.greencheckasn_set.filter(active=True).first()

    # then: resulting Hostingprovider is the one linked to the original request
    assert hp.id == pr.provider.id

    # and: the active ASN is the same one that was attached before,
    # not a newly created one
    assert original_asn.id == post_approval_asn.id


@pytest.mark.django_db
def test_approve_updates_existing_provider_without_deleting_ips(
    hosting_provider_with_sample_user,
):
    # given: existing ips linked to our provider
    active_ip = GreenIpFactory.create(hostingprovider=hosting_provider_with_sample_user)
    inactive_ip = GreenIpFactory.create(
        hostingprovider=hosting_provider_with_sample_user, active=False
    )
    hosting_provider_with_sample_user.save()

    assert active_ip in hosting_provider_with_sample_user.greencheckip_set.all()
    assert inactive_ip in hosting_provider_with_sample_user.greencheckip_set.all()

    # given: a provider request linked to an existing hosting provider
    pr = ProviderRequestFactory.create(
        services=faker.words(nb=4), provider=hosting_provider_with_sample_user
    )
    ProviderRequestLocationFactory.create(request=pr)
    ProviderRequestEvidenceFactory.create(request=pr)
    ProviderRequestIPRangeFactory(
        start=active_ip.ip_start, end=active_ip.ip_end, request=pr
    )
    ProviderRequestIPRangeFactory(
        start=inactive_ip.ip_start, end=inactive_ip.ip_end, request=pr
    )

    # when: the request is approved
    result = pr.approve()
    hp = models.Hostingprovider.objects.get(id=result.id)
    # and: I fetch provider request IP ranges
    pr_ips = hp.greencheckip_set.all()

    # then: resulting Hostingprovider is the one linked to the original request
    assert hp.id == pr.provider.id

    # and: the active ip is the same one that was attached before
    assert active_ip.id in [ip.id for ip in pr_ips]
    # and: the inactive ip is the same one that was attached before
    assert inactive_ip.id in [ip.id for ip in pr_ips]


@pytest.mark.django_db
def test_approve_updates_existing_provider_without_deleting_supporting_evidence(
    hosting_provider_with_sample_user,
):
    # given: a provider request linked to an existing hosting provider

    original_evidence = SupportingEvidenceFactory.create(
        hostingprovider=hosting_provider_with_sample_user
    )

    assert original_evidence.id in [
        evidence.id
        for evidence in hosting_provider_with_sample_user.supporting_documents.all()
    ]

    # given: a provider request linked to an existing hosting provider
    pr = ProviderRequestFactory.create(
        services=faker.words(nb=4), provider=hosting_provider_with_sample_user
    )
    # and: a location
    ProviderRequestLocationFactory.create(request=pr)
    # and: a matching piece of supporting evidence
    pr_original_evidence = ProviderRequestEvidenceFactory.create(
        request=pr,
        title=original_evidence.title,
        description=original_evidence.description,
        public=original_evidence.public,
        type=original_evidence.type,
        file=original_evidence.attachment,
        link=original_evidence.url,
    )

    # when: the request is approved
    result = pr.approve()
    hp = models.Hostingprovider.objects.get(id=result.id)

    updated_hp_evidence = hp.supporting_documents.all()

    # then we should have the same item of evidence that was attached to the
    # provider still associated, rather than being deleted and replaced with
    # a similar but new one
    assert original_evidence.id in [evidence.id for evidence in updated_hp_evidence]


@pytest.mark.django_db
def test_approve_supports_orgs_not_offering_hosted_services():
    # given: a verification request for an organisation that does
    # not offer any services, but we still want ot recognise as green
    other_none_service = ServiceFactory(
        slug="other-none",
        name="Other: we do not offer any of these services",
    )
    pr = ProviderRequestFactory.create(services=[other_none_service])

    ProviderRequestLocationFactory.create(request=pr)
    ProviderRequestEvidenceFactory.create(request=pr)

    # when: the request is approved
    result = pr.approve()
    hp = models.Hostingprovider.objects.get(id=result.id)

    # provider is visible by default
    # appropriate labels and services are listed
    assert hp.is_listed is False
    assert "up-to-date" in hp.staff_labels.slugs()
    assert "other-none" in hp.services.slugs()


@pytest.mark.django_db
def test_approve_creates_ip_ranges():
    # given: a provider request with multiple IP ranges
    pr = ProviderRequestFactory.create()
    ProviderRequestLocationFactory.create(request=pr)
    ProviderRequestEvidenceFactory.create(request=pr)

    ip1 = ProviderRequestIPRangeFactory.create(request=pr)
    ip2 = ProviderRequestIPRangeFactory.create(request=pr)
    ip3 = ProviderRequestIPRangeFactory.create(request=pr)

    # when: the request is approved
    result = pr.approve()
    hp = models.Hostingprovider.objects.get(id=result.id)

    # then: IP ranges are created
    for ip_range in [ip1, ip2, ip3]:
        assert hp.greencheckip_set.filter(
            ip_start=ip_range.start, ip_end=ip_range.end, active=True
        ).exists()


@pytest.mark.django_db
def test_approve_creates_asns():
    # given: a provider request with multiple locations, IP ranges, ASNs, evidence and consent
    pr = ProviderRequestFactory.create()
    ProviderRequestLocationFactory.create(request=pr)
    ProviderRequestEvidenceFactory.create(request=pr)

    asn1 = ProviderRequestASNFactory.create(request=pr)
    asn2 = ProviderRequestASNFactory.create(request=pr)
    asn2 = ProviderRequestASNFactory.create(request=pr)

    # when: the request is approved
    result = pr.approve()
    hp = models.Hostingprovider.objects.get(id=result.id)

    # then: ASNs are created
    for asn in [asn1, asn2]:
        assert hp.greencheckasn_set.filter(asn=asn.asn, active=True).exists()


@freeze_time("Feb 15th, 2023")
@pytest.mark.django_db
def test_approve_creates_evidence_documents():
    # given: a provider request with multiple locations, IP ranges, ASNs, evidence and consent
    pr = ProviderRequestFactory.create()
    ProviderRequestLocationFactory.create(request=pr)

    ev1 = ProviderRequestEvidenceFactory.create(request=pr)
    ev2 = ProviderRequestEvidenceFactory.create(
        request=pr,
        link=None,
        file=SimpleUploadedFile(name=faker.file_name(), content=faker.text().encode()),
    )

    # given: we are frozen in time
    today = date(2023, 2, 15)
    a_year_from_now = date(2024, 2, 15)

    # when: the request is approved
    result = pr.approve()
    hp = models.Hostingprovider.objects.get(id=result.id)

    # then: evidence documents are created and configured as expected
    evidence_with_link = hp.supporting_documents.filter(
        title=ev1.title, description=ev1.description
    ).get()
    evidence_with_file = hp.supporting_documents.filter(
        title=ev2.title, description=ev2.description
    ).get()

    assert evidence_with_link.url == ev1.link
    assert evidence_with_link.public == ev1.public
    assert evidence_with_link.type == ev1.type
    assert evidence_with_link.valid_from == today
    assert evidence_with_link.valid_to == a_year_from_now

    assert evidence_with_file.attachment == ev2.file
    assert evidence_with_file.public == ev2.public
    assert evidence_with_file.type == ev2.type
    assert evidence_with_file.valid_from == today
    assert evidence_with_file.valid_to == a_year_from_now


@freeze_time("Feb 15th, 2023")
@pytest.mark.django_db
def test_approve_creates_new_evidence_when_existing_evidence_updated(
    hosting_provider_with_sample_user,
):
    """
    When a user updates an existing piece of evidence by changing the attached evidence
    in the verification wizard, we should create a new piece of evidence,
    rather than updating the existing one.
    See trello card: https://trello.com/c/1Q6Z2Q8V
    """
    # given: a provider request with multiple locations, IP ranges, ASNs, evidence and consent
    provider = hosting_provider_with_sample_user
    pr = ProviderRequestFactory.create(provider=provider)
    ProviderRequestLocationFactory.create(request=pr)

    # and: a piece of evidence that is already associated with the provider
    initial_evidence_upload = SimpleUploadedFile(
        name=faker.file_name(), content=faker.text().encode()
    )
    provider_evidence = SupportingEvidenceFactory.create(
        attachment=initial_evidence_upload,
        type="Annual Report",
        hostingprovider=hosting_provider_with_sample_user,
        public=True,
    )

    # and: new evidence in the provider request, one of which has the same name
    # as the existing evidence, but a different attachment
    updated_evidence_upload = SimpleUploadedFile(
        name=faker.file_name(), content=faker.text().encode()
    )

    ev1 = ProviderRequestEvidenceFactory.create(request=pr)
    ev2 = ProviderRequestEvidenceFactory.create(
        request=pr,
        link=None,
        title=provider_evidence.title,
        type=provider_evidence.type,
        public=provider_evidence.public,
        file=updated_evidence_upload,
    )

    # given: we are frozen in time
    today = date(2023, 2, 15)
    a_year_from_now = date(2024, 2, 15)

    # when: the request is approved, returning our provider
    result = pr.approve()
    hp = models.Hostingprovider.objects.get(id=result.id)
    supporting_docs = hp.supporting_documents.all()

    # then: the previous evidence with the same name should also be visible
    assert provider_evidence not in supporting_docs
    assert len(supporting_docs) == 2


@freeze_time("Feb 15th, 2023")
@pytest.mark.django_db
def test_approve_skips_duplicate_evidence_when_existing_evidence_updated(
    hosting_provider_with_sample_user,
):
    """
    When a user updates an existing piece of evidence by changing the attached evidence,
    we should create a new piece of evidence, rather than updating the existing one.
    See trello card: https://trello.com/c/1Q6Z2Q8V
    And issue

    """
    # given: a provider request with multiple locations, IP ranges, ASNs, evidence and consent
    provider = hosting_provider_with_sample_user
    pr = ProviderRequestFactory.create(provider=provider)
    ProviderRequestLocationFactory.create(request=pr)

    # and: a piece of evidence that is already associated with the provider
    initial_evidence_description = faker.text().encode()
    initial_evidence_upload = SimpleUploadedFile(
        name=faker.file_name(), content=initial_evidence_description
    )
    provider_evidence = SupportingEvidenceFactory.create(
        attachment=initial_evidence_upload,
        type="Annual Report",
        hostingprovider=hosting_provider_with_sample_user,
        public=True,
    )

    ev1 = ProviderRequestEvidenceFactory.create(request=pr)
    ev2 = ProviderRequestEvidenceFactory.create(
        request=pr,
        link=None,
        title=provider_evidence.title,
        type=provider_evidence.type,
        public=provider_evidence.public,
        file=initial_evidence_upload,
    )

    # given: we are frozen in time
    today = date(2023, 2, 15)
    a_year_from_now = date(2024, 2, 15)

    # when: the request is approved, returning our provider

    result = pr.approve()
    hp = models.Hostingprovider.objects.get(id=result.id)
    supporting_docs = hp.supporting_documents.all()
    # and the previous evidence with the same name should also be visible
    assert len(supporting_docs) == 2
    assert provider_evidence in supporting_docs

    # and the provider evidence should have the


@pytest.mark.django_db
def test_wizard_view_with_just_network_explanation(
    user,
    client,
    wizard_form_org_details_data,
    wizard_form_org_location_data,
    wizard_form_services_data,
    wizard_form_verification_bases_data,
    wizard_form_evidence_data,
    wizard_form_network_explanation_only,
    wizard_form_consent,
    wizard_form_preview,
):
    client.force_login(user)

    form_data = [
        wizard_form_org_details_data,
        wizard_form_org_location_data,
        wizard_form_services_data,
        wizard_form_verification_bases_data,
        wizard_form_evidence_data,
        wizard_form_network_explanation_only,
        wizard_form_consent,
        wizard_form_preview,
    ]
    # when: a multi step submission has been successfully completed
    response = _create_provider_request(client, form_data)

    # then: a ProviderRequest object exists in the db
    pr = response.context_data["providerrequest"]
    pr_from_db = models.ProviderRequest.objects.get(id=pr.id)

    # and it's the same one as in our HTTP response
    pr.id == pr_from_db.id

    # then we have our explanation saved to the provider
    explanation = wizard_form_network_explanation_only.get(
        "extra__5-missing_network_explanation"
    )

    assert pr.missing_network_explanation == explanation
    assert pr_from_db.missing_network_explanation == explanation


@pytest.mark.django_db
def test_wizard_records_if_location_import_needed(
    user,
    client,
    wizard_form_org_details_data,
    wizard_form_org_location_data,
    wizard_form_services_data,
    wizard_form_verification_bases_data,
    wizard_form_evidence_data,
    wizard_form_network_data,
    wizard_form_consent,
    wizard_form_preview,
):
    """
    Given: a working set of data
    When: a user has flagged up that they have too many locations to add manually
    Then: the provider request captures this detail
    """

    # given: valid form data and authenticated user
    form_data = [
        wizard_form_org_details_data,
        wizard_form_org_location_data,
        wizard_form_services_data,
        wizard_form_verification_bases_data,
        wizard_form_evidence_data,
        wizard_form_network_data,
        wizard_form_consent,
        wizard_form_preview,
    ]
    client.force_login(user)

    # when: a multi step submission has been successfully completed
    response = _create_provider_request(client, form_data)

    pr = response.context_data["providerrequest"]
    assert models.ProviderRequest.objects.filter(id=pr.id).exists()

    pr_from_db = models.ProviderRequest.objects.filter(id=pr.id).first()

    assert pr_from_db.location_import_required is True


@pytest.mark.django_db
def test_new_submission_doesnt_modify_available_services(
    user,
    client,
    wizard_form_org_details_data,
    wizard_form_org_location_data,
    wizard_form_services_data,
    wizard_form_verification_bases_data,
    wizard_form_evidence_data,
    wizard_form_network_data,
    wizard_form_consent,
    wizard_form_preview,
):
    # given: existing list of available services
    services = models.Service.objects.all()

    # given: valid form data and authenticated user
    form_data = [
        wizard_form_org_details_data,
        wizard_form_org_location_data,
        wizard_form_services_data,
        wizard_form_verification_bases_data,
        wizard_form_evidence_data,
        wizard_form_network_data,
        wizard_form_consent,
        wizard_form_preview,
    ]
    client.force_login(user)

    # when: a multi step submission has been successfully completed
    response = _create_provider_request(client, form_data)

    pr = response.context_data["providerrequest"]
    pr_from_db = models.ProviderRequest.objects.filter(id=pr.id).first()

    # then: all services in the new request already existed in the db
    assert all(service in services for service in pr_from_db.services.all())
    # then: no new services were created in the db
    assert set(models.Service.objects.all()) == set(services)


@pytest.mark.django_db
def test_edit_view_accessible_by_creator(client):
    # given: an open provider request
    pr = ProviderRequestFactory.create()

    # when: accessing its edit view by the creator
    client.force_login(pr.created_by)
    response = client.get(urls.reverse("provider_request_edit", args=[str(pr.id)]))

    # then: page for the correct provider request is rendered
    assert response.status_code == 200


@pytest.mark.django_db
def test_edit_view_accessible_by_admin(client, greenweb_staff_user):
    # given: an open provider request
    pr = ProviderRequestFactory.create()

    # when: accessing its edit view by Green Web staff
    client.force_login(greenweb_staff_user)
    response = client.get(urls.reverse("provider_request_edit", args=[str(pr.id)]))

    # then: page for the correct provider request is rendered
    assert response.status_code == 200


@pytest.mark.django_db
def test_edit_view_inaccessible_by_other_users(client, user):
    # given: an open provider request
    pr = ProviderRequestFactory.create()

    # when: accessing its edit view by regular users other than the creator
    client.force_login(user)
    response = client.get(urls.reverse("provider_request_edit", args=[str(pr.id)]))

    # then: we pretend this request does not exist and show 404
    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    "request_status,status_code",
    [
        (models.ProviderRequestStatus.OPEN, 200),
        (models.ProviderRequestStatus.PENDING_REVIEW, 302),
        (models.ProviderRequestStatus.APPROVED, 302),
    ],
    ids=["open-accessible", "pending_review-inaccessible", "approved-inaccessible"],
)
def test_edit_view_accessible_for_given_status(client, request_status, status_code):
    # given: a provider request with a given status
    pr = ProviderRequestFactory.create(status=request_status)

    # when: accessing the edit view by its creator
    client.force_login(pr.created_by)
    response = client.get(urls.reverse("provider_request_edit", args=[str(pr.id)]))

    # then: response with an expected status code is returned
    assert response.status_code == status_code


@pytest.mark.django_db
def test_edit_view_displays_form_with_prepopulated_data(client):
    # given: an open provider request
    pr = ProviderRequestFactory.create()

    # when: accessing the edit view by its creator
    client.force_login(pr.created_by)
    response = client.get(urls.reverse("provider_request_edit", args=[str(pr.id)]))

    # then: rendered form (we only check the first page)
    # contains pre-filled data about the original request
    form = response.context_data["form"]
    assert form.instance == pr

    expected_initial = {
        "name": pr.name,
        "website": pr.website,
        "description": pr.description,
        "authorised_by_org": pr.authorised_by_org,
    }
    assert form.initial == expected_initial


@pytest.mark.django_db
def test_editing_pr_updates_original_submission(
    client,
    wizard_form_org_details_data,
    wizard_form_services_data,
    wizard_form_verification_bases_data,
    wizard_form_evidence_data,
    wizard_form_network_data,
    wizard_form_consent,
    wizard_form_preview,
):
    """
    This is an end-to-end test verifying that:
    - edit view for an existing ProviderRequest displays
        initial data correctly for each step
    - ModelForms and ModelFormsets in consecutive steps are bound
        to correct "instance" or "queryset" respectively.

    Initial data for ProviderRequest is created in the test,
    data used for updating the object is injected as wizard_form_* fixtures.
    """
    # given: an open provider request
    pr = ProviderRequestFactory.create(services=["service1", "service2"])

    loc1 = ProviderRequestLocationFactory.create(request=pr)
    loc2 = ProviderRequestLocationFactory.create(request=pr)

    ev1 = ProviderRequestEvidenceFactory.create(request=pr)
    ev2 = ProviderRequestEvidenceFactory.create(request=pr)

    ip1 = ProviderRequestIPRangeFactory.create(request=pr)
    ip2 = ProviderRequestIPRangeFactory.create(request=pr)
    ip3 = ProviderRequestIPRangeFactory.create(request=pr)

    asn = ProviderRequestASNFactory.create(request=pr)

    # given: URL of the edit view of the existing PR
    edit_url = urls.reverse("provider_request_edit", args=[str(pr.id)])

    # when: accessing the edit view by its creator
    client.force_login(pr.created_by)
    response = client.get(edit_url)

    # then: ORG_DETAILS form is bound with an instance, initial data is displayed
    org_details_form = response.context_data["form"]
    assert org_details_form.instance == pr
    assert org_details_form.initial == {
        "name": pr.name,
        "website": pr.website,
        "description": pr.description,
        "authorised_by_org": pr.authorised_by_org,
    }
    # when: submitting ORG_DETAILS form with overridden data
    response = client.post(edit_url, wizard_form_org_details_data, follow=True)

    # then: wizard proceeds, LOCATIONS formset is displayed with bound queryset and initial data
    locations_formset = response.context_data["form"].forms["locations"]
    assert set(locations_formset.queryset) == set([loc1, loc2])
    assert locations_formset.forms[0].initial == {
        "name": loc1.name,
        "city": loc1.city,
        "country": loc1.country,
    }
    assert locations_formset.forms[1].initial == {
        "name": loc2.name,
        "city": loc2.city,
        "country": loc2.country,
    }

    # when: submitting LOCATIONS form with overridden data
    # data to override locations: delete existing 2 locations, add 3 new ones
    wizard_form_org_location_data = {
        "provider_request_wizard_view-current_step": "1",
        "locations__1-TOTAL_FORMS": "5",
        "locations__1-INITIAL_FORMS": "2",
        "locations__1-0-country": loc1.country.code,
        "locations__1-0-city": loc1.city,
        "locations__1-0-id": str(loc1.id),
        "locations__1-0-DELETE": "on",
        "locations__1-1-country": loc2.country.code,
        "locations__1-1-city": loc2.city,
        "locations__1-1-id": str(loc2.id),
        "locations__1-1-DELETE": "on",
        "locations__1-2-country": faker.country_code(),
        "locations__1-2-city": faker.city(),
        "locations__1-3-country": faker.country_code(),
        "locations__1-3-city": faker.city(),
        "locations__1-4-country": faker.country_code(),
        "locations__1-4-city": faker.city(),
        "extra__1-location_import_required": "True",
    }
    response = client.post(edit_url, wizard_form_org_location_data, follow=True)

    # then: wizard proceeds, SERVICES form is displayed with bound instance and initial data
    services_form = response.context_data["form"]
    assert services_form.instance == pr
    assert services_form.initial == {"services": ["service1", "service2"]}
    # when: submitting SERVICES form with overridden data
    response = client.post(edit_url, wizard_form_services_data, follow=True)

    # then: wizard proceeds, VERIFICATION BASIS form is displayed
    response = client.post(edit_url, wizard_form_verification_bases_data, follow=True)

    # then: wizards proceeds, EVIDENCE formset is displayed with bound queryset and initial data
    evidence_formset = response.context_data["form"]
    assert set(evidence_formset.queryset) == set([ev1, ev2])
    # we strip expected initial data from "file" key for comparison purposes
    # because {'file': <FieldFile: None>} != {'file': <FieldFile: None>}
    ev1_initial = {
        "title": ev1.title,
        "description": ev1.description,
        "link": ev1.link,
        "type": ev1.type,
        "public": ev1.public,
    }
    ev2_initial = {
        "title": ev2.title,
        "description": ev2.description,
        "link": ev2.link,
        "type": ev2.type,
        "public": ev2.public,
    }
    assert ev1_initial.items() <= evidence_formset.forms[0].initial.items()
    assert ev2_initial.items() <= evidence_formset.forms[1].initial.items()

    # when: submitting EVIDENCE step with overridden data
    response = client.post(edit_url, wizard_form_evidence_data, follow=True)

    # then: wizard proceeds, NETWORK form is displayed
    # and child forms/formsets have queryset/instance and initial data assigned
    network_form = response.context_data["form"]
    ip_formset = network_form.forms["ips"]
    assert set(ip_formset.queryset) == set([ip1, ip2, ip3])

    asn_formset = network_form.forms["asns"]
    assert set([asn]) == set(asn_formset.queryset)

    extra_network_form = network_form.forms["extra"]
    assert extra_network_form.instance == pr
    assert extra_network_form.initial == {
        "missing_network_explanation": pr.missing_network_explanation,
        "network_import_required": pr.network_import_required,
    }

    # when: submitting NETWORK step with overridden data
    response = client.post(edit_url, wizard_form_network_data, follow=True)

    # then: wizard proceeds, CONSENT step is displayed with correct instance/initial data assigned
    consent_form = response.context_data["form"]
    assert consent_form.instance == pr
    assert consent_form.initial == {
        "data_processing_opt_in": pr.data_processing_opt_in,
        "newsletter_opt_in": pr.newsletter_opt_in,
    }

    # when: submitting CONSENT step with overridden data
    response = client.post(edit_url, wizard_form_consent, follow=True)

    # then: PREVIEW step is rendered with correct data
    preview_form_dict = response.context_data["preview_forms"]

    # org_detail preview displays overridden data
    overridden_values = {
        "name": wizard_form_org_details_data["0-name"],
        "description": wizard_form_org_details_data["0-description"],
        "website": wizard_form_org_details_data["0-website"],
    }
    assert overridden_values.items() <= preview_form_dict["0"].initial.items()

    # locations preview displays overridden data
    location_forms = preview_form_dict["1"].forms["locations"].forms
    # 5 forms in total are passed, 3 of them not marked as deleted
    assert len(location_forms) == 5
    assert len([form for form in location_forms if not form["DELETE"].value()]) == 3

    # when: PREVIEW form is submitted
    response = client.post(edit_url, wizard_form_preview, follow=True)

    # then: submitting the final step redirects to the detail view
    assert response.resolver_match.func.view_class is views.ProviderRequestDetailView

    # then: a ProviderRequest object is updated in the db
    pr_id = response.context_data["providerrequest"].id
    updated_pr = models.ProviderRequest.objects.get(id=pr_id)
    assert updated_pr.name == overridden_values["name"]
    assert updated_pr.providerrequestlocation_set.count() == 3


@pytest.mark.django_db
def test_provider_edit_view_accessible_by_user_with_required_perms(
    client, hosting_provider_with_sample_user, sample_hoster_user
):
    # given: existing hosting provider with assigned user
    # when: accessing its edit view by that user
    client.force_login(sample_hoster_user)
    response = client.get(
        urls.reverse("provider_edit", args=[str(hosting_provider_with_sample_user.id)])
    )

    # then: page for the correct provider request is rendered
    assert response.status_code == 200


@pytest.mark.django_db
def test_provider_edit_view_accessible_by_admins(
    client, hosting_provider_with_sample_user, greenweb_staff_user
):
    # given: existing hosting provider with assigned user
    # when: accessing its edit view by GWF staff
    client.force_login(greenweb_staff_user)
    response = client.get(
        urls.reverse("provider_edit", args=[str(hosting_provider_with_sample_user.id)])
    )

    # then: page for the correct provider request is rendered
    assert response.status_code == 200


@pytest.mark.django_db
def test_provider_edit_view_inaccessible_by_unauthorized_users(
    client, hosting_provider_with_sample_user
):
    # given: existing hosting provider with assigned user
    # when: accessing its edit view by another user
    another_user = UserFactory.build()
    another_user.save()

    client.force_login(another_user)
    response = client.get(
        urls.reverse("provider_edit", args=[str(hosting_provider_with_sample_user.id)])
    )

    # then: user is redirected to the provider portal
    assert response.status_code == 302


@pytest.mark.django_db
def test_edit_view_inaccessible_for_nonexistent_provider(client, greenweb_staff_user):
    client.force_login(greenweb_staff_user)
    response = client.get(urls.reverse("provider_edit", args=[str(123456)]))

    # then: user is redirected to the provider portal
    assert response.status_code == 404


@pytest.mark.django_db
def test_editing_hp_creates_new_verification_request(
    client,
    hosting_provider_with_sample_user,
    sorted_ips,
    wizard_form_org_details_data,
    wizard_form_services_data,
    wizard_form_verification_bases_data,
    wizard_form_evidence_data,
    wizard_form_network_data,
    wizard_form_consent,
    wizard_form_preview,
    mailoutbox,
):
    """
    This is an end-to-end test verifying that edit view for
    an existing HostingProvider displays initial data correctly for each step.


    Initial data for HostingProvider is created in the test,
    data used for updating the object is injected as wizard_form_* fixtures.
    """
    # given: URL of the edit view of the existing HP
    hp = hosting_provider_with_sample_user
    ev1 = SupportingEvidenceFactory.create(hostingprovider=hp)
    ev2 = SupportingEvidenceFactory.create(hostingprovider=hp)
    ip1 = GreenIpFactory.create(
        ip_start=sorted_ips[0], ip_end=sorted_ips[1], hostingprovider=hp
    )
    ip2 = GreenIpFactory.create(
        ip_start=sorted_ips[1], ip_end=sorted_ips[2], hostingprovider=hp
    )
    ip3 = GreenIpFactory.create(
        ip_start=sorted_ips[2], ip_end=sorted_ips[3], hostingprovider=hp
    )
    asn = GreenASNFactory.create(hostingprovider=hp)

    edit_url = urls.reverse("provider_edit", args=[str(hp.id)])

    # when: accessing the edit view by its creator
    client.force_login(hp.created_by)
    response = client.get(edit_url)

    # then: ORG_DETAILS form is bound with an instance, initial data is displayed
    org_details_form = response.context_data["form"]
    assert org_details_form.initial == {
        "name": hp.name,
        "website": hp.website,
        "description": hp.description,
    }
    # when: submitting ORG_DETAILS form with overridden data
    response = client.post(edit_url, wizard_form_org_details_data, follow=True)

    # then: wizard proceeds, LOCATIONS formset is displayed with initial data
    locations_formset = response.context_data["form"].forms["locations"]
    assert locations_formset.forms[0].initial == {
        "city": hp.city,
        "country": hp.country,
    }

    # when: submitting LOCATIONS form with overridden data
    # data to override locations: delete existing location, add 3 new ones
    wizard_form_org_location_data = {
        "provider_request_wizard_view-current_step": "1",
        "locations__1-TOTAL_FORMS": "4",
        "locations__1-INITIAL_FORMS": "1",
        "locations__1-0-country": hp.country.code,
        "locations__1-0-city": "Berlin",
        "locations__1-0-id": "",
        "locations__1-0-DELETE": "on",
        "locations__1-1-country": faker.country_code(),
        "locations__1-1-city": faker.city(),
        "locations__1-2-country": faker.country_code(),
        "locations__1-2-city": faker.city(),
        "locations__1-3-country": faker.country_code(),
        "locations__1-3-city": faker.city(),
        "extra__1-location_import_required": "True",
    }
    response = client.post(edit_url, wizard_form_org_location_data, follow=True)
    # then: wizard proceeds, SERVICES form is displayed with initial data
    services_form = response.context_data["form"]
    assert services_form.initial == {"services": []}
    # when: submitting SERVICES form with overridden data
    response = client.post(edit_url, wizard_form_services_data, follow=True)

    # then: wizard proceeds, VERIFICATION BASIS form is displayed with initial data
    response = client.post(edit_url, wizard_form_verification_bases_data, follow=True)

    # then: wizards proceeds, EVIDENCE formset is displayed with initial data
    evidence_formset = response.context_data["form"]
    # we strip expected initial data from "file" key for comparison purposes
    # because {'file': <FieldFile: None>} != {'file': <FieldFile: None>}
    ev1_initial = {
        "title": ev1.title,
        "description": ev1.description,
        "link": ev1.link,
        "type": ev1.type,
        "public": ev1.public,
    }
    ev2_initial = {
        "title": ev2.title,
        "description": ev2.description,
        "link": ev2.link,
        "type": ev2.type,
        "public": ev2.public,
    }

    assert ev1_initial.items() <= evidence_formset.forms[0].initial.items()
    assert ev2_initial.items() <= evidence_formset.forms[1].initial.items()

    # when: submitting EVIDENCE step with overridden data
    response = client.post(edit_url, wizard_form_evidence_data, follow=True)

    # then: wizard proceeds, NETWORK form is displayed
    # and child forms/formsets have initial data assigned
    network_form = response.context_data["form"]
    ip_formset = network_form.forms["ips"]
    # GOTCHA: ModelFormSets created with initial data will store that
    # in initial_extra
    assert ip_formset.initial_extra == [
        {"start": ip1.ip_start, "end": ip1.ip_end},
        {"start": ip2.ip_start, "end": ip2.ip_end},
        {"start": ip3.ip_start, "end": ip3.ip_end},
    ]

    asn_formset = network_form.forms["asns"]
    assert asn_formset.initial_extra == [{"asn": asn.asn}]

    extra_network_form = network_form.forms["extra"]
    assert extra_network_form.initial == {}

    # when: submitting NETWORK step with overridden data
    response = client.post(edit_url, wizard_form_network_data, follow=True)

    # then: wizard proceeds, CONSENT step is displayed with correct instance/initial data assigned
    consent_form = response.context_data["form"]
    assert consent_form.initial == {}

    # when: submitting CONSENT step with overridden data
    response = client.post(edit_url, wizard_form_consent, follow=True)

    # then: PREVIEW step is rendered with correct data
    preview_form_dict = response.context_data["preview_forms"]

    # org_detail preview displays overridden data
    overridden_values = {
        "name": wizard_form_org_details_data["0-name"],
        "description": wizard_form_org_details_data["0-description"],
        "website": wizard_form_org_details_data["0-website"],
    }
    assert overridden_values.items() <= preview_form_dict["0"].initial.items()

    # locations preview displays overridden data
    location_forms = preview_form_dict["1"].forms["locations"].forms
    # 4 forms in total are passed, 3 of them not marked as deleted
    assert len(location_forms) == 4
    assert len([form for form in location_forms if not form["DELETE"].value()]) == 3

    # when: PREVIEW form is submitted
    response = client.post(edit_url, wizard_form_preview, follow=True)

    # then: submitting the final step redirects to the detail view
    assert response.resolver_match.func.view_class is views.ProviderRequestDetailView

    # then: a ProviderRequest object is updated in the db
    pr_id = response.context_data["providerrequest"].id
    updated_pr = models.ProviderRequest.objects.get(id=pr_id)
    assert updated_pr.name == overridden_values["name"]
    assert updated_pr.providerrequestlocation_set.count() == 3

    # and: we should see an email sent to the hosting provider
    assert len(mailoutbox) == 1
    email = mailoutbox[0]
    email_copy = "update the listing for"
    html_content = email.alternatives[0][0]

    # and: email txt and html should acknowledge the request being an update
    assert email_copy in email.body
    assert email_copy in html_content


@pytest.mark.django_db
def test_saving_changes_to_verification_request_from_hp_via_wizard(
    client,
    hosting_provider_with_sample_user,
    sorted_ips,
    wizard_form_org_details_data,
    wizard_form_services_data,
    wizard_form_verification_bases_data,
    wizard_form_evidence_data,
    wizard_form_network_data,
    wizard_form_consent,
    wizard_form_preview,
    fake_evidence,
    mailoutbox,
):
    """
    Support the case where we are making changes to save back to
    a provider. At the end of this test, the verification request
    should reflect: the updated evidence, fewer IP ranges and so on,
    ready to save back to the hosting provider
    """

    # given: A hosting provider with corresponding evidence already in the
    # database
    hp = hosting_provider_with_sample_user
    ev1 = SupportingEvidenceFactory.create(hostingprovider=hp)
    ev2 = SupportingEvidenceFactory.create(hostingprovider=hp)
    ip1 = GreenIpFactory.create(
        ip_start=sorted_ips[0], ip_end=sorted_ips[1], hostingprovider=hp
    )
    ip2 = GreenIpFactory.create(
        ip_start=sorted_ips[1], ip_end=sorted_ips[2], hostingprovider=hp
    )
    ip3 = GreenIpFactory.create(
        ip_start=sorted_ips[2], ip_end=sorted_ips[3], hostingprovider=hp
    )
    asn = GreenASNFactory.create(hostingprovider=hp)

    prev_green_ip_vals = hp.greencheckip_set.all().values()
    prev_green_asn_vals = hp.greencheckasn_set.all().values()
    prev_supporting_docs_vals = hp.supporting_documents.values()
    prev_service_vals = hp.services.all().values()

    assert len(prev_green_ip_vals) == 3
    assert len(prev_green_asn_vals) == 1
    assert len(prev_supporting_docs_vals) == 2
    assert len(prev_service_vals) == 0

    # given: URL of the edit view of the existing HP
    edit_url = urls.reverse("provider_edit", args=[str(hp.id)])

    # when: accessing the edit view by its creator
    client.force_login(hp.created_by)
    response = client.get(edit_url)

    # and: submitting ORG_DETAILS form with overridden data
    response = client.post(edit_url, wizard_form_org_details_data, follow=True)

    # then: when wizard proceeds, LOCATIONS formset is displayed with
    # initial data
    locations_formset = response.context_data["form"].forms["locations"]
    assert locations_formset.forms[0].initial == {
        "city": hp.city,
        "country": hp.country,
    }

    # when: submitting LOCATIONS form with overridden data
    # data to override locations: delete existing location, add 3 new ones
    wizard_form_org_location_data = {
        "provider_request_wizard_view-current_step": "1",
        "locations__1-TOTAL_FORMS": "4",
        "locations__1-INITIAL_FORMS": "1",
        "locations__1-0-country": hp.country.code,
        "locations__1-0-city": "Berlin",
        "locations__1-0-id": "",
        "locations__1-0-DELETE": "on",
        "locations__1-1-country": faker.country_code(),
        "locations__1-1-city": faker.city(),
        "locations__1-2-country": faker.country_code(),
        "locations__1-2-city": faker.city(),
        "locations__1-3-country": faker.country_code(),
        "locations__1-3-city": faker.city(),
        "extra__1-location_import_required": "True",
    }
    response = client.post(edit_url, wizard_form_org_location_data, follow=True)

    # then: wizard proceeds, SERVICES form is displayed with initial data
    services_form = response.context_data["form"]
    assert services_form.initial == {"services": []}
    # when: submitting SERVICES form with overridden data
    response = client.post(edit_url, wizard_form_services_data, follow=True)

    # then: wizard proceeds, VERIFICATION BASES form is displayed with initial data
    verification_bases_form = response.context_data["form"]
    assert isinstance(verification_bases_form, account_forms.BasisForVerificationForm)

    # when: submitting VERIFICATION BASES form with overridden data
    response = client.post(edit_url, wizard_form_verification_bases_data, follow=True)

    # then: wizards proceeds,
    # when: EVIDENCE formset is displayed with initial data
    evidence_formset = response.context_data["form"]

    assert isinstance(evidence_formset, account_forms.GreenEvidenceForm)

    # when: submitting EVIDENCE step with one piece of overridden data
    # and one saved data
    updated_evidence_data = {
        "provider_request_wizard_view-current_step": "4",
        "4-TOTAL_FORMS": 2,
        "4-INITIAL_FORMS": 0,
        # first an existing piece of evidence from ev1
        "4-0-title": ev1.title,
        "4-0-link": ev1.url,
        "4-0-file": "",
        "4-0-type": ev1.type,
        "4-0-public": ev1.public,
        # then a new piece of evidence
        "4-1-title": " ".join(faker.words(3)),
        "4-1-link": "",
        "4-1-file": fake_evidence,
        "4-1-type": models.EvidenceType.ANNUAL_REPORT.value,
        "4-1-public": "on",
    }

    response = client.post(edit_url, updated_evidence_data, follow=True)

    # then: wizard proceeds, NETWORK form is displayed
    # and child forms/formsets have initial data assigned
    network_form = response.context_data["form"]
    assert isinstance(network_form, account_forms.NetworkFootprintForm)

    ip_formset = network_form.forms["ips"]
    for formset_form in ip_formset.forms:
        assert isinstance(formset_form, account_forms.IpRangeForm)

    assert ip_formset.initial_extra == [
        {"start": ip1.ip_start, "end": ip1.ip_end},
        {"start": ip2.ip_start, "end": ip2.ip_end},
        {"start": ip3.ip_start, "end": ip3.ip_end},
    ]

    asn_formset = network_form.forms["asns"]
    for formset_form in asn_formset.forms:
        assert isinstance(formset_form, account_forms.AsnForm)

    assert asn_formset.initial_extra == [{"asn": asn.asn}]

    extra_network_form = network_form.forms["extra"]
    assert isinstance(extra_network_form, account_forms.ExtraNetworkInfoForm)
    assert extra_network_form.initial == {}

    # when: submitting NETWORK step with overridden data, where we
    # have one less IP  range than before
    modified_network_data = {
        "provider_request_wizard_view-current_step": "5",
        "ips__5-TOTAL_FORMS": "2",
        "ips__5-INITIAL_FORMS": "0",
        "ips__5-0-start": ip1.ip_start,
        "ips__5-0-end": ip1.ip_end,
        "ips__5-1-start": ip2.ip_start,
        "ips__5-1-end": ip2.ip_end,
        "asns__5-TOTAL_FORMS": "1",
        "asns__5-INITIAL_FORMS": "0",
        "asns__5-0-asn": asn.asn,
    }

    response = client.post(edit_url, modified_network_data, follow=True)

    # then: wizard proceeds, CONSENT step is displayed with correct instance/initial data assigned
    consent_form = response.context_data["form"]
    assert isinstance(consent_form, account_forms.ConsentForm)
    assert consent_form.initial == {}

    # when: submitting CONSENT step with data
    response = client.post(edit_url, wizard_form_consent, follow=True)

    # org_detail preview displays overridden data
    overridden_values = {
        "name": wizard_form_org_details_data["0-name"],
        "description": wizard_form_org_details_data["0-description"],
        "website": wizard_form_org_details_data["0-website"],
    }

    # when: PREVIEW form is submitted
    response = client.post(edit_url, wizard_form_preview, follow=True)

    # then: a ProviderRequest object is updated in the db
    pr_id = response.context_data["providerrequest"].id
    updated_pr = models.ProviderRequest.objects.get(id=pr_id)

    # and: we should see the updated name
    assert updated_pr.name == wizard_form_org_details_data["0-name"]

    # and: we should see 2 IP ranges and 1 ASN
    assert updated_pr.providerrequestiprange_set.count() == 2
    assert updated_pr.providerrequestasn_set.count() == 1

    # and: we should see 3 services listed
    assert updated_pr.providerrequestservice_set.count() == 3

    # and: we should see 2 pieces of evidence, where one is from the original
    # hosting provider, and the other a newly supplied one
    assert updated_pr.providerrequestevidence_set.count() == 2
    # and the values from the first piece of evidence in this test, ev1 correspond
    # with the first piece of evidence in the verification request
    vr_evidence_set = updated_pr.providerrequestevidence_set.all()
    assert ev1.title in [ev.title for ev in vr_evidence_set]
    assert ev1.link in [ev.link for ev in vr_evidence_set]

    # and: we should see 3 locations,
    assert updated_pr.providerrequestlocation_set.count() == 3

    # and: we should see an email sent to the hosting provider
    assert len(mailoutbox) == 1
    email = mailoutbox[0]
    email_copy = "update the listing for"
    html_content = email.alternatives[0][0]

    # and: email txt and html should acknowledge the request being an update
    assert email_copy in email.body
    assert email_copy in html_content


@pytest.mark.django_db
def test_saving_changes_to_hp_with_new_verification_request(
    client,
    hosting_provider_with_sample_user,
    sorted_ips,
    wizard_form_org_details_data,
    wizard_form_services_data,
    wizard_form_verification_bases_data,
    wizard_form_evidence_data,
    wizard_form_network_data,
    wizard_form_consent,
    wizard_form_preview,
    fake_evidence,
):
    """
    Check that the updated verification request when approved saves changes
    to the hosting provider as we expect
    """
    # given: A hosting provider with corresponding evidence already in the
    # database
    hp = hosting_provider_with_sample_user
    ev1 = SupportingEvidenceFactory.create(hostingprovider=hp)
    ev2 = SupportingEvidenceFactory.create(hostingprovider=hp)
    ip1 = GreenIpFactory.create(
        ip_start=sorted_ips[0], ip_end=sorted_ips[1], hostingprovider=hp
    )
    ip2 = GreenIpFactory.create(
        ip_start=sorted_ips[1], ip_end=sorted_ips[2], hostingprovider=hp
    )
    ip3 = GreenIpFactory.create(
        ip_start=sorted_ips[2], ip_end=sorted_ips[3], hostingprovider=hp
    )
    asn = GreenASNFactory.create(hostingprovider=hp)

    logger.debug(ev1)
    logger.debug(ev2)

    # given: URL of the edit view of the existing HP
    edit_url = urls.reverse("provider_edit", args=[str(hp.id)])

    # when: accessing the edit view by its creator
    client.force_login(hp.created_by)
    response = client.get(edit_url)

    # and: submitting ORG_DETAILS form with overridden data
    response = client.post(edit_url, wizard_form_org_details_data, follow=True)

    # then: when wizard proceeds, LOCATIONS formset is displayed with
    # initial data
    locations_formset = response.context_data["form"].forms["locations"]

    # when: submitting LOCATIONS form with overridden data
    # data to override locations: delete existing location, add 3 new ones
    wizard_form_org_location_data = {
        "provider_request_wizard_view-current_step": "1",
        "locations__1-TOTAL_FORMS": "4",
        "locations__1-INITIAL_FORMS": "1",
        "locations__1-0-country": hp.country.code,
        "locations__1-0-city": "Berlin",
        "locations__1-0-id": "",
        "locations__1-0-DELETE": "on",
        "locations__1-1-country": faker.country_code(),
        "locations__1-1-city": faker.city(),
        "locations__1-2-country": faker.country_code(),
        "locations__1-2-city": faker.city(),
        "locations__1-3-country": faker.country_code(),
        "locations__1-3-city": faker.city(),
        "extra__1-location_import_required": "True",
    }
    response = client.post(edit_url, wizard_form_org_location_data, follow=True)

    # then: wizard proceeds, SERVICES form is displayed with initial data
    services_form = response.context_data["form"]
    assert services_form.initial == {"services": []}
    # when: submitting SERVICES form with overridden data
    response = client.post(edit_url, wizard_form_services_data, follow=True)

    # when: submitting VERIFICATION BASES form with overridden data
    response = client.post(edit_url, wizard_form_verification_bases_data, follow=True)

    # then: wizards proceeds,
    # when: EVIDENCE formset is displayed with initial data
    evidence_formset = response.context_data["form"]

    assert isinstance(evidence_formset, account_forms.GreenEvidenceForm)

    # when: submitting EVIDENCE step with one piece of overridden data
    # and one saved data
    updated_evidence_data = {
        "provider_request_wizard_view-current_step": "4",
        "4-TOTAL_FORMS": 2,
        "4-INITIAL_FORMS": 0,
        # first an existing piece of evidence from ev1
        "4-0-title": ev1.title,
        "4-0-link": ev1.url,
        "4-0-file": "",
        "4-0-type": ev1.type,
        "4-0-public": ev1.public,
        #4then a new piece of evidence
        "4-1-title": " ".join(faker.words(3)),
        "4-1-link": "",
        "4-1-file": fake_evidence,
        "4-1-type": models.EvidenceType.ANNUAL_REPORT.value,
        "4-1-public": "on",
    }

    response = client.post(edit_url, updated_evidence_data, follow=True)

    # then: wizard proceeds, NETWORK form is displayed
    # and child forms/formsets have initial data assigned
    network_form = response.context_data["form"]
    assert isinstance(network_form, account_forms.NetworkFootprintForm)

    ip_formset = network_form.forms["ips"]
    for formset_form in ip_formset.forms:
        assert isinstance(formset_form, account_forms.IpRangeForm)

    assert ip_formset.initial_extra == [
        {"start": ip1.ip_start, "end": ip1.ip_end},
        {"start": ip2.ip_start, "end": ip2.ip_end},
        {"start": ip3.ip_start, "end": ip3.ip_end},
    ]

    asn_formset = network_form.forms["asns"]
    for formset_form in asn_formset.forms:
        assert isinstance(formset_form, account_forms.AsnForm)

    assert asn_formset.initial_extra == [{"asn": asn.asn}]

    extra_network_form = network_form.forms["extra"]
    assert isinstance(extra_network_form, account_forms.ExtraNetworkInfoForm)
    assert extra_network_form.initial == {}

    # when: submitting NETWORK step with overridden data, where we
    # have one less IP  range than before
    modified_network_data = {
        "provider_request_wizard_view-current_step": "5",
        "ips__5-TOTAL_FORMS": "2",
        "ips__5-INITIAL_FORMS": "0",
        "ips__5-0-start": ip1.ip_start,
        "ips__5-0-end": ip1.ip_end,
        "ips__5-1-start": ip2.ip_start,
        "ips__5-1-end": ip2.ip_end,
        "asns__5-TOTAL_FORMS": "1",
        "asns__5-INITIAL_FORMS": "0",
        "asns__5-0-asn": asn.asn,
    }

    response = client.post(edit_url, modified_network_data, follow=True)

    # then: wizard proceeds, CONSENT step is displayed with correct instance/initial data assigned
    consent_form = response.context_data["form"]
    assert isinstance(consent_form, account_forms.ConsentForm)
    assert consent_form.initial == {}

    # when: submitting CONSENT step with data
    response = client.post(edit_url, wizard_form_consent, follow=True)

    # org_detail preview displays overridden data
    overridden_values = {
        "name": wizard_form_org_details_data["0-name"],
        "description": wizard_form_org_details_data["0-description"],
        "website": wizard_form_org_details_data["0-website"],
    }

    # when: PREVIEW form is submitted
    response = client.post(edit_url, wizard_form_preview, follow=True)

    # then: a ProviderRequest object is updated in the db
    pr_id = response.context_data["providerrequest"].id
    updated_pr = models.ProviderRequest.objects.get(id=pr_id)

    # and: we should see the updated name
    assert updated_pr.name == wizard_form_org_details_data["0-name"]

    # and: we should see 2 IP ranges and 1 ASN
    assert updated_pr.providerrequestiprange_set.count() == 2
    assert updated_pr.providerrequestasn_set.count() == 1

    # and: we should see 3 services listed
    assert updated_pr.providerrequestservice_set.count() == 3

    # and: we should see 2 pieces of evidence, where one is from the original
    # hosting provider, and the other a newly supplied one
    assert updated_pr.providerrequestevidence_set.count() == 2
    # and the values from the first piece of evidence in this test, ev1 correspond
    # with the first piece of evidence in the verification request
    vr_evidence_set = updated_pr.providerrequestevidence_set.all()
    assert ev1.title in [ev.title for ev in vr_evidence_set]
    assert ev1.link in [ev.link for ev in vr_evidence_set]

    # and: we should see 3 locations,
    assert updated_pr.providerrequestlocation_set.count() == 3

    # given: an approved provider request

    updated_hp = updated_pr.approve()

    # then: we should see the updated provider name
    assert updated_pr.name == updated_hp.name

    # and: we should see the same number of updated ip ranges
    assert updated_hp.active_ip_ranges().count() == 2

    # and: our provided ip ranges should be in the updated provider
    updated_hp_ips = updated_hp.active_ip_ranges()
    updated_pr_ips = updated_pr.providerrequestiprange_set.all()

    assert updated_hp_ips.count() == updated_pr_ips.count()

    for ip_range in updated_hp_ips:
        assert ip_range.ip_start in [ip.start for ip in updated_pr_ips]
        assert ip_range.ip_end in [ip.end for ip in updated_pr_ips]

    # and: our dropped ip range should no longer be in the updated provider
    assert ip3.ip_start not in [ip.start for ip in updated_pr_ips]
    assert ip3.ip_end not in [ip.end for ip in updated_pr_ips]

    # and: the same ASN should be on both
    updated_pr_green_asns = updated_pr.providerrequestasn_set.all()
    updated_pr_green_asns = updated_hp.greencheckasn_set.all()

    for green_as in updated_pr_green_asns:
        assert green_as.asn in [asn.asn for asn in updated_pr_green_asns]

    updated_pr_evidence_set = updated_pr.providerrequestevidence_set.all()
    updated_hp_evidence_set = updated_hp.supporting_documents.all()

    # and: we have same evidence on the provider as was on the
    # verification request
    for ev in updated_hp_evidence_set:
        assert ev.title in [pr_ev.title for pr_ev in updated_pr_evidence_set]
        if not ev.url:
            pr_file_urls = [
                pr_ev.file.url for pr_ev in updated_pr_evidence_set if pr_ev.file
            ]
            assert ev.attachment.url in pr_file_urls

    # and: one piece of evidence from the original provider remains

    # and: ev2, the old piece of evidence is no longer in the updated provider
    assert ev2.title not in [pr_ev.title for pr_ev in updated_pr_evidence_set]
    assert ev2.link not in [pr_ev.link for pr_ev in updated_pr_evidence_set]

    # and: an updated list of services
    updated_hp_services_names = updated_hp.services.names()
    updated_pr_services = updated_pr.providerrequestservice_set.all()
    updated_pr_service_names = [svc.tag.name for svc in updated_pr_services]

    for service in updated_hp_services_names:
        assert service in updated_pr_service_names

    # and: an updated country and city combination is set on the provider
    pr_first_location = updated_pr.providerrequestlocation_set.first()
    assert pr_first_location.country == updated_hp.country
    assert pr_first_location.city == updated_hp.city


@pytest.mark.skip(reason="pending")
def test_other_hosting_provider_with_no_city_creates_location():
    """
    hosting provider with just a country should show the city and country
    """
    pass


@pytest.mark.skip(reason="pending")
def test_request_from_hosting_provider_with_loads_of_IP_ranges():
    """
    hosting provider has loads of IP ranges more than is reasonable
    to add manually. we dont' want them to appear as NONE on the preview
    """
    pass


@pytest.mark.skip(reason="pending")
def test_request_from_host_provider_finishes_in_sensible_time():
    """
    hosting provider with just a country should show the city and country
    """
    pass


@pytest.mark.django_db
@pytest.mark.parametrize(
    "provider_exists, email_copy, email_subject_copy",
    (
        (
            True,
            "taking the time to update",
            "Update to the Green Web Dataset has been approved",
        ),
        (
            False,
            "taking the time to submit",
            "Verification request to the Green Web Dataset is approved",
        ),
    ),
)
def test_email_sent_on_approval(
    hosting_provider_with_sample_user,
    greenweb_staff_user,
    provider_request_factory,
    rf,
    mailoutbox,
    provider_exists,
    email_copy,
    email_subject_copy,
):
    """
    Given: a provider request to update an existing provider
    When: it is approved by staff, we should send an email
    Then: We should see content referring to the updated request,
    not a totally new request
    """

    if provider_exists:
        pr = provider_request_factory.create(provider=hosting_provider_with_sample_user)
    else:
        pr = provider_request_factory.create()

    ProviderRequestLocationFactory.create(request=pr)

    pr_admin = ac_admin.ProviderRequest(
        models.ProviderRequest, admin_site.greenweb_admin
    )

    admin_update_path = reverse(
        "greenweb_admin:accounts_providerrequest_change", args=[pr.id]
    )

    # create our request and add the user simulating them
    # being logged in
    req = rf.get(admin_update_path)
    req.user = greenweb_staff_user

    # we need to add a session middleware to the request
    # without this attempts to place a message in the request
    # for the staff user will fail in this test
    middleware = SessionMiddleware(lambda req: HttpResponse())

    middleware.process_request(req)
    messages = FallbackStorage(req)
    req._messages = messages

    queryset = models.ProviderRequest.objects.filter(id=pr.id)

    # simulate the admin approving the request
    pr_admin.mark_approved(req, queryset)

    # do we have the expected number of emails?
    assert len(mailoutbox) == 1

    email = mailoutbox[0]

    # do we have our expected email subject?

    assert email_subject_copy in email.subject

    # Does our content refer to the correct copy?
    assert email_copy in email.body

    # And does the html as well?
    html_content = email.alternatives[0][0]
    assert email_copy in html_content


@pytest.mark.django_db
@pytest.mark.parametrize(
    "provider_exists, email_copy, email_subject_copy",
    (
        (
            True,
            "taking the time to update",
            "Update to the Green Web Dataset has been approved",
        ),
        (
            False,
            "taking the time to submit",
            "Verification request to the Green Web Dataset is approved",
        ),
    ),
)
def test_email_request_email_confirmation_is_sent(
    hosting_provider_with_sample_user,
    greenweb_staff_user,
    provider_request_factory,
    rf,
    mailoutbox,
    provider_exists,
    email_copy,
    email_subject_copy,
):
    """
    Given: a provider request is being created by the user
    When: they submit it
    Then: An email should be sent confirming the submission, with
    copy matching whether a new, or existing provider
    """

    if provider_exists:
        pr = provider_request_factory.create(provider=hosting_provider_with_sample_user)
    else:
        pr = provider_request_factory.create()

    ProviderRequestLocationFactory.create(request=pr)

    pr_admin = ac_admin.ProviderRequest(
        models.ProviderRequest, admin_site.greenweb_admin
    )

    admin_update_path = reverse(
        "greenweb_admin:accounts_providerrequest_change", args=[pr.id]
    )

    # create our request and add the user simulating them
    # being logged in
    req = rf.get(admin_update_path)
    req.user = greenweb_staff_user

    # we need to add a session middleware to the request
    # without this attempts to place a message in the request
    # for the staff user will fail in this test
    middleware = SessionMiddleware(lambda req: HttpResponse())
    middleware.process_request(req)
    messages = FallbackStorage(req)
    req._messages = messages

    queryset = models.ProviderRequest.objects.filter(id=pr.id)

    # simulate the admin approving the request
    pr_admin.mark_approved(req, queryset)

    # do we have the expected number of emails?
    assert len(mailoutbox) == 1

    email = mailoutbox[0]

    # do we have our expected email subject?
    assert email_subject_copy in email.subject

    # Does our content refer to the correct copy?
    assert email_copy in email.body

    # And does the html as well?
    html_content = email.alternatives[0][0]
    assert email_copy in html_content


@pytest.mark.django_db
@pytest.mark.parametrize(
    "staff_action,expected_status",
    (
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("removed", "Removed"),
        ("open", "Changes Requested"),
    ),
)
def test_staff_review_is_logged(
    hosting_provider_with_sample_user,
    greenweb_staff_user,
    provider_request_factory,
    rf,
    staff_action,
    expected_status,
):
    """
    When a staff member reviews a provider request, and rejects, approves or
    otherwise makes a decision, about the validity we should see this logged
    in the audit log
    """

    # Given: a provider request created by a hosting provider
    pr = provider_request_factory.create(provider=hosting_provider_with_sample_user)
    ProviderRequestLocationFactory.create(request=pr)

    # And: a staff user logged into the admin, viewing the verification request
    pr_admin = ac_admin.ProviderRequest(
        models.ProviderRequest, admin_site.greenweb_admin
    )
    admin_update_path = reverse(
        "greenweb_admin:accounts_providerrequest_change", args=[pr.id]
    )
    req = rf.get(admin_update_path)
    req.user = greenweb_staff_user

    # we need to add a session middleware to the request
    # without this attempts to place a message in the request
    # for the staff user will fail in this test
    middleware = SessionMiddleware(lambda req: HttpResponse())
    middleware.process_request(req)
    messages = FallbackStorage(req)
    req._messages = messages

    queryset = models.ProviderRequest.objects.filter(id=pr.id)

    # When: the staff member makes a decision on the request's validity
    getattr(pr_admin, f"mark_{staff_action}")(req, queryset)

    # Then: we should see the entry in the audit log for the request
    log_message = LogEntry.objects.get(object_id=pr.id)

    assert ContentType.objects.get_for_model(pr).pk == log_message.content_type_id
    assert log_message.user == greenweb_staff_user
    assert log_message.action_flag == CHANGE
    assert log_message.change_message == expected_status


@override_flag("upstream_providers", active=True)
@pytest.mark.django_db
def test_wizard_submission_with_upstream_providers(
    user,
    client,
    wizard_form_org_details_data,
    wizard_form_org_location_data,
    wizard_form_services_data,
    wizard_form_verification_bases_with_linked_provider_data,
    wizard_form_evidence_data,
    wizard_form_network_data,
    wizard_form_consent,
    wizard_form_preview,
):
    """
    Given: a user submits a provider request selecting linked upstream providers
    When: the wizard completes successfully
    Then: the ProviderRequest is created with the linked providers persisted
    """
    form_data = [
        wizard_form_org_details_data,
        wizard_form_org_location_data,
        wizard_form_services_data,
        wizard_form_verification_bases_with_linked_provider_data,
        wizard_form_evidence_data,
        wizard_form_network_data,
        wizard_form_consent,
        wizard_form_preview,
    ]
    client.force_login(user)

    response = _create_provider_request(client, form_data)

    pr = response.context_data["providerrequest"]
    pr_from_db = models.ProviderRequest.objects.get(id=pr.id)

    assert pr_from_db.upstream_providers.count() == 1
    assert pr_from_db.upstream_providers.first().name == "Upstream Green Provider"


@pytest.mark.django_db
def test_wizard_submission_without_upstream_providers(
    user,
    client,
    wizard_form_org_details_data,
    wizard_form_org_location_data,
    wizard_form_services_data,
    wizard_form_verification_bases_data,
    wizard_form_evidence_data,
    wizard_form_network_data,
    wizard_form_consent,
    wizard_form_preview,
):
    """
    Given: a user submits a provider request without selecting linked providers
    When: the wizard completes successfully
    Then: the ProviderRequest is created with no linked providers
    """
    form_data = [
        wizard_form_org_details_data,
        wizard_form_org_location_data,
        wizard_form_services_data,
        wizard_form_verification_bases_data,
        wizard_form_evidence_data,
        wizard_form_network_data,
        wizard_form_consent,
        wizard_form_preview,
    ]
    client.force_login(user)

    response = _create_provider_request(client, form_data)

    pr = response.context_data["providerrequest"]
    pr_from_db = models.ProviderRequest.objects.get(id=pr.id)

    assert pr_from_db.upstream_providers.count() == 0


# ---------- upstream_providers feature-flag tests ----------

@pytest.mark.django_db
def test_wizard_basis_step_hides_upstream_providers_when_flag_is_off(
    user,
    client,
    wizard_form_org_details_data,
    wizard_form_org_location_data,
    wizard_form_services_data,
):
    """
    Given: the upstream_providers waffle flag is OFF
    When: the basis-for-verification step is rendered
    Then: the upstream_providers field and disclosure are not present
    """
    client.force_login(user)

    response = client.post(urls.reverse("provider_registration"), wizard_form_org_details_data, follow=True)
    assert response.status_code == 200

    response = client.post(urls.reverse("provider_registration"), wizard_form_org_location_data, follow=True)
    assert response.status_code == 200

    response = client.post(urls.reverse("provider_registration"), wizard_form_services_data, follow=True)
    assert response.status_code == 200

    assert response.context_data["wizard"]["steps"].current == "3"
    form = response.context_data["form"]
    assert "upstream_providers" not in form.fields
    assert "country" not in form.fields
    assert "Linked providers" not in response.content.decode()


@override_flag("upstream_providers", active=True)
@pytest.mark.django_db
def test_wizard_basis_step_shows_upstream_providers_when_flag_is_on(
    user,
    client,
    wizard_form_org_details_data,
    wizard_form_org_location_data,
    wizard_form_services_data,
):
    """
    Given: the upstream_providers waffle flag is ON
    When: the basis-for-verification step is rendered
    Then: the upstream_providers field and disclosure are present
    """
    client.force_login(user)

    response = client.post(urls.reverse("provider_registration"), wizard_form_org_details_data, follow=True)
    assert response.status_code == 200

    response = client.post(urls.reverse("provider_registration"), wizard_form_org_location_data, follow=True)
    assert response.status_code == 200

    response = client.post(urls.reverse("provider_registration"), wizard_form_services_data, follow=True)
    assert response.status_code == 200

    assert response.context_data["wizard"]["steps"].current == "3"
    form = response.context_data["form"]
    assert "upstream_providers" in form.fields

    # we check for evidence of the code that toggles visibility on upstream providers selector
    content = response.content.decode()

    assert "toggleUpstreamProvidersSection" in content


@override_flag("upstream_providers", active=True)
@pytest.mark.django_db
def test_wizard_preview_shows_upstream_providers(
    user,
    client,
    wizard_form_org_details_data,
    wizard_form_org_location_data,
    wizard_form_services_data,
    wizard_form_verification_bases_with_linked_provider_data,
    wizard_form_evidence_data,
    wizard_form_network_data,
    wizard_form_consent,
):
    """
    Given: a user selects upstream providers during the wizard
    When: the preview step is rendered
    Then: the upstream provider names are visible on the preview page
    """
    client.force_login(user)

    form_data = [
        wizard_form_org_details_data,
        wizard_form_org_location_data,
        wizard_form_services_data,
        wizard_form_verification_bases_with_linked_provider_data,
        wizard_form_evidence_data,
        wizard_form_network_data,
        wizard_form_consent,
    ]

    response = None
    for data in form_data:
        response = client.post(urls.reverse("provider_registration"), data, follow=True)
        assert response.status_code == 200

    # then: PREVIEW step is rendered
    preview_forms = response.context_data["preview_forms"]
    basis_form = preview_forms["3"]
    assert "upstream_providers" in basis_form.fields

    # the upstream provider name should appear in the rendered content
    content = response.content.decode()
    assert "Upstream Green Provider" in content


@pytest.mark.django_db
def test_request_detail_hides_upstream_providers_when_flag_is_off(
    user,
    client,
):
    """
    Given: a ProviderRequest has upstream_providers but the flag is OFF
    When: the detail page is viewed
    Then: the Linked providers row is not visible
    """
    upstream = models.Hostingprovider.objects.create(
        name="Upstream Provider",
        country="GB",
        archived=False,
        is_listed=True,
        website="https://example.com",
    )
    pr = models.ProviderRequest.objects.create(
        name="Test Provider",
        website="https://test.com",
        description="Test",
        created_by=user,
        status="PENDING_REVIEW",
        authorised_by_org=True,
    )
    pr.upstream_providers.add(upstream)

    client.force_login(user)
    detail_url = urls.reverse("provider_request_detail", args=[pr.id])
    response = client.get(detail_url)
    assert response.status_code == 200
    assert "Linked providers" not in response.content.decode()
    # DB should still have the data
    pr.refresh_from_db()
    assert pr.upstream_providers.count() == 1


@override_flag("upstream_providers", active=True)
@pytest.mark.django_db
def test_request_detail_shows_upstream_providers_when_flag_is_on(
    user,
    client,
):
    """
    Given: a ProviderRequest has upstream_providers and the flag is ON
    When: the detail page is viewed
    Then: the Linked providers row is visible
    """
    upstream = models.Hostingprovider.objects.create(
        name="Upstream Provider",
        country="GB",
        archived=False,
        is_listed=True,
        website="https://example.com",
    )
    pr = models.ProviderRequest.objects.create(
        name="Test Provider",
        website="https://test.com",
        description="Test",
        created_by=user,
        status="PENDING_REVIEW",
        authorised_by_org=True,
    )
    pr.upstream_providers.add(upstream)

    client.force_login(user)
    detail_url = urls.reverse("provider_request_detail", args=[pr.id])
    response = client.get(detail_url)
    assert response.status_code == 200
    content = response.content.decode()
    assert "Linked providers" in content
    assert "Upstream Provider" in content


@pytest.mark.django_db
def test_provider_edit_anonymous_user_does_not_500(client, hosting_provider_factory):
    """
    Given an anonymous user and an existing hosting provider,
    when they access the provider edit URL,
    then they are redirected to the login page and no 500 error is raised.
    The dispatch method accesses request.user.is_admin,
    which would previously raise AttributeError on AnonymousUser.
    """
    provider = hosting_provider_factory.create()
    edit_url = urls.reverse("provider_edit", args=[provider.id])
    response = client.get(edit_url)

    assert response.status_code == 302


# ---------------------------------------------------------------------------
# Verification basis versioning (October 2026 rollout)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_active_version_defaults_to_june_when_no_request():
    """
    Given no request is available,
    get_active_version falls back to the June 2026 version
    rather than risk evaluating the waffle flag against a None request.
    """
    from apps.accounts.models import get_active_version, VerificationBasisVersion

    assert get_active_version(None) == VerificationBasisVersion.JUNE_2026


@pytest.mark.django_db
def test_verification_bases_choices_returns_2026_06_when_flag_off(user):
    """
    Given the verification_basis_v2 flag is OFF (the default),
    get_verification_bases_choices returns only June 2026 bases,
    even when October 2026 bases exist in the database.
    """
    from apps.accounts.models import VerificationBasisVersion

    june_base = VerificationBasisFactory.create(
        name="June self generation test",
        version=VerificationBasisVersion.JUNE_2026,
    )
    october_base = VerificationBasisFactory.create(
        name="October self generation test",
        version=VerificationBasisVersion.OCTOBER_2026,
    )

    request = RequestFactory().get("/")
    request.user = user

    choices = models.ProviderRequest.get_verification_bases_choices(request)
    choice_slugs = {slug for slug, _label in choices}

    assert june_base.slug in choice_slugs
    assert october_base.slug not in choice_slugs


@pytest.mark.django_db
@override_flag("verification_basis_v2", active=True)
def test_verification_bases_choices_returns_2026_10_when_flag_on(user):
    """
    Given the verification_basis_v2 flag is ON,
    get_verification_bases_choices returns only October 2026 bases,
    even when June 2026 bases exist in the database.
    """
    from apps.accounts.models import VerificationBasisVersion

    june_base = VerificationBasisFactory.create(
        name="June direct procurement test",
        version=VerificationBasisVersion.JUNE_2026,
    )
    october_base = VerificationBasisFactory.create(
        name="October direct procurement test",
        version=VerificationBasisVersion.OCTOBER_2026,
    )

    request = RequestFactory().get("/")
    request.user = user

    choices = models.ProviderRequest.get_verification_bases_choices(request)
    choice_slugs = {slug for slug, _label in choices}

    assert october_base.slug in choice_slugs
    assert june_base.slug not in choice_slugs


@pytest.mark.django_db
def test_verification_bases_choices_per_user_rollout_via_m2m(user):
    """
    Regression test: per-user rollout via the waffle flag's ``users`` M2M
    must actually take effect. ``everyone`` must be ``None`` (the migration
    default), not ``False`` — waffle's ``Flag.is_active`` short-circuits at
    ``everyone is False`` and never consults the ``users`` / ``groups``
    relations, which would silently break the documented rollout strategy.

    This test mirrors how an admin rolls the flag out to a specific user
    (via the waffle admin UI), as opposed to ``@override_flag`` which
    bypasses the M2M by setting ``everyone`` directly.
    """
    from apps.accounts.models import VerificationBasisVersion
    from waffle.models import Flag

    june_base = VerificationBasisFactory.create(
        name="June passive procurement m2m test",
        version=VerificationBasisVersion.JUNE_2026,
    )
    october_base = VerificationBasisFactory.create(
        name="October passive procurement m2m test",
        version=VerificationBasisVersion.OCTOBER_2026,
    )

    flag = Flag.objects.get(name="verification_basis_v2")
    # invariant upheld by migration 0104: everyone must be None for per-user
    # rollout to work. Assert here so a future migration edit can't silently
    # break rollout without a test failure.
    assert flag.everyone is None, (
        "verification_basis_v2 flag.everyone must be None (not False) for "
        "per-user rollout via the users M2M to take effect. See migration 0104."
    )
    flag.users.add(user)
    flag.save()
    # clear any cached flag state on the request object
    request = RequestFactory().get("/")
    request.user = user

    choices = models.ProviderRequest.get_verification_bases_choices(request)
    choice_slugs = {slug for slug, _label in choices}

    assert october_base.slug in choice_slugs
    assert june_base.slug not in choice_slugs


@pytest.mark.django_db
def test_verification_bases_choices_with_request_none_returns_june():
    """
    Given no request is passed (e.g. class-level callable invocation),
    get_verification_bases_choices returns only June 2026 bases.
    """
    from apps.accounts.models import VerificationBasisVersion

    VerificationBasisFactory.create(
        name="June green tariff test",
        version=VerificationBasisVersion.JUNE_2026,
    )
    october_base = VerificationBasisFactory.create(
        name="October green tariff test",
        version=VerificationBasisVersion.OCTOBER_2026,
    )

    choices = models.ProviderRequest.get_verification_bases_choices()
    choice_slugs = {slug for slug, _label in choices}

    assert october_base.slug not in choice_slugs


@pytest.mark.django_db
def test_october_2026_bases_carry_documentation_links():
    """
    The October 2026 verification bases seeded by migration 0105 each carry a
    ``required_evidence_link`` pointing at the public documentation page for
    that criterion, mirroring how the June 2026 bases expose evidence
    guidance. The ``label`` property appends this as a
    "see required evidence" hyperlink so end users can reach the docs from
    the form.
    """
    from apps.accounts.models import VerificationBasisVersion

    expected = {
        "Self generation": (
            "https://www.thegreenwebfoundation.org/verification/disclosures/"
            "self-generation"
        ),
        "Direct procurement": (
            "https://www.thegreenwebfoundation.org/verification/disclosures/"
            "direct-procurement"
        ),
        "Green tariffs": (
            "https://www.thegreenwebfoundation.org/verification/disclosures/"
            "green-tariff"
        ),
        "Unbundled certificates": (
            "https://www.thegreenwebfoundation.org/verification/disclosures/"
            "unbundled-certificates"
        ),
        "Passive procurement": (
            "https://www.thegreenwebfoundation.org/verification/disclosures/"
            "passive-procurement"
        ),
    }

    october_bases = models.VerificationBasis.objects.filter(
        version=VerificationBasisVersion.OCTOBER_2026
    )
    # sanity: we seeded exactly the five expected bases
    assert october_bases.count() == len(expected)

    for base in october_bases:
        assert base.name in expected, f"unexpected October base: {base.name!r}"
        link = base.required_evidence_link
        assert link == expected[base.name], (
            f"{base.name}: required_evidence_link={link!r}, "
            f"expected {expected[base.name]!r}"
        )

        # the label property should surface the link as a "see required evidence"
        # hyperlink so users can reach the docs from the wizard form
        rendered = str(base.label)
        assert link in rendered
        assert "see required evidence" in rendered.lower()


@pytest.mark.django_db
@override_flag("verification_basis_v2", active=True)
def test_wizard_basis_step_shows_documentation_links_for_october_bases(
    user,
    client,
    wizard_form_org_details_data,
    wizard_form_org_location_data,
    wizard_form_services_data,
):
    """
    Given the verification_basis_v2 flag is ON,
    when the basis-for-verification step is rendered,
    then each October 2026 checkbox label includes a hyperlink to that
    criterion's documentation page.
    """
    client.force_login(user)

    client.post(urls.reverse("provider_registration"), wizard_form_org_details_data, follow=True)
    client.post(urls.reverse("provider_registration"), wizard_form_org_location_data, follow=True)
    response = client.post(
        urls.reverse("provider_registration"), wizard_form_services_data, follow=True
    )

    assert response.status_code == 200
    assert response.context_data["wizard"]["steps"].current == "3"

    content = response.content.decode()
    # every October basis should surface a "see required evidence" link in the form
    for path in (
        "/verification/disclosures/self-generation",
        "/verification/disclosures/direct-procurement",
        "/verification/disclosures/green-tariff",
        "/verification/disclosures/unbundled-certificates",
        "/verification/disclosures/passive-procurement",
    ):
        assert path in content, (
            f"expected documentation link {path!r} in the rendered basis step"
        )
    assert "see required evidence" in content


@pytest.mark.django_db
@override_flag("verification_basis_v2", active=True)
def test_basis_form_drops_legacy_initial_when_flag_on(user):
    """
    Given the verification_basis_v2 flag is ON, initial ``verification_bases``
    slugs that belong to the legacy June 2026 version are dropped so the form
    does not pre-check options that cannot validate against the October 2026
    choices. This matters when editing an existing provider or request that
    was submitted under the old criteria.
    """
    from apps.accounts.forms.provider_request_wizard import (
        BasisForVerificationForm,
    )
    from apps.accounts.models import VerificationBasisVersion

    june_base = VerificationBasisFactory.create(
        name="June legacy basis for initial drop test",
        version=VerificationBasisVersion.JUNE_2026,
    )
    october_base = VerificationBasisFactory.create(
        name="October active basis for initial drop test",
        version=VerificationBasisVersion.OCTOBER_2026,
    )

    request = RequestFactory().get("/")
    request.user = user

    form = BasisForVerificationForm(
        initial={"verification_bases": [june_base.slug, october_base.slug]},
        request=request,
    )

    assert october_base.slug in form.initial["verification_bases"]
    assert june_base.slug not in form.initial["verification_bases"]


@pytest.mark.django_db
@override_flag("verification_basis_v2", active=True)
def test_basis_form_drops_all_legacy_initial_when_no_october_match(user):
    """
    Given the flag is ON and the initial bases are all legacy (June 2026),
    the form clears ``verification_bases`` to an empty list rather than
    carrying forward slugs that can't validate.
    """
    from apps.accounts.forms.provider_request_wizard import (
        BasisForVerificationForm,
    )
    from apps.accounts.models import VerificationBasisVersion

    june_base = VerificationBasisFactory.create(
        name="June only legacy for clear test",
        version=VerificationBasisVersion.JUNE_2026,
    )

    request = RequestFactory().get("/")
    request.user = user

    form = BasisForVerificationForm(
        initial={"verification_bases": [june_base.slug]},
        request=request,
    )

    assert form.initial["verification_bases"] == []


@pytest.mark.django_db
def test_basis_form_preserves_initial_when_flag_off(user):
    """
    Given the flag is OFF (the default), initial June 2026 slugs are
    preserved — the filtering only applies when the flag is ON.
    """
    from apps.accounts.forms.provider_request_wizard import (
        BasisForVerificationForm,
    )
    from apps.accounts.models import VerificationBasisVersion

    june_base = VerificationBasisFactory.create(
        name="June preserved when flag off test",
        version=VerificationBasisVersion.JUNE_2026,
    )

    request = RequestFactory().get("/")
    request.user = user

    form = BasisForVerificationForm(
        initial={"verification_bases": [june_base.slug]},
        request=request,
    )

    assert june_base.slug in form.initial["verification_bases"]


# ---------------------------------------------------------------------------
# Disclosure matching + claim coverage (verification_basis_v2 rollout)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_evidence_new_fields_default_to_none():
    """
    A fresh ProviderRequestEvidence defaults both new fields to None,
    so the migration is additive and existing rows remain valid.
    """
    pr = ProviderRequestFactory.create()
    evidence = models.ProviderRequestEvidence.objects.create(
        title="Untitled evidence",
        link="https://example.com/evidence",
        type=models.EvidenceType.WEB_PAGE.value,
        public=False,
        request=pr,
    )
    assert evidence.fossil_free_energy_matching is None
    assert evidence.claim_coverage_percentage is None


@pytest.mark.django_db
def test_evidence_round_trips_matching_and_coverage_on_request():
    """
    ProviderRequestEvidence can persist and reload both new fields.
    """
    pr = ProviderRequestFactory.create()
    evidence = models.ProviderRequestEvidence.objects.create(
        title="Round trip evidence",
        link="https://example.com/evidence",
        type=models.EvidenceType.WEB_PAGE.value,
        public=True,
        request=pr,
        fossil_free_energy_matching=models.FossilFreeEnergyMatching.HOURLY.value,
        claim_coverage_percentage=42,
    )
    evidence.refresh_from_db()
    assert evidence.fossil_free_energy_matching == models.FossilFreeEnergyMatching.HOURLY.value
    assert evidence.claim_coverage_percentage == 42


@pytest.mark.django_db
def test_supporting_document_round_trips_matching_and_coverage():
    """
    HostingProviderSupportingDocument inherits the new fields from
    AbstractSupportingDocument and persists both.
    """
    doc = models.HostingProviderSupportingDocument.objects.create(
        title="Provider doc",
        type=models.EvidenceType.CERTIFICATE.value,
        valid_from=date(2023, 1, 1),
        valid_to=date(2024, 1, 1),
        fossil_free_energy_matching=models.FossilFreeEnergyMatching.ANNUAL.value,
        claim_coverage_percentage=100,
    )
    doc.refresh_from_db()
    assert doc.fossil_free_energy_matching == models.FossilFreeEnergyMatching.ANNUAL.value
    assert doc.claim_coverage_percentage == 100


@pytest.mark.django_db
def test_claim_coverage_percentage_rejects_above_100():
    """
    The model-level MaxValueValidator enforces the 100 cap on save/full_clean.
    """
    pr = ProviderRequestFactory.create()
    evidence = models.ProviderRequestEvidence(
        title="Over-coverage",
        link="https://example.com/evidence",
        type=models.EvidenceType.WEB_PAGE.value,
        public=False,
        request=pr,
        claim_coverage_percentage=101,
    )
    with pytest.raises(ValidationError):
        evidence.full_clean()


# --- Form ---


@pytest.mark.django_db
def test_credential_form_hides_matching_fields_when_flag_off(user):
    """
    With verification_basis_v2 OFF (the default), the two new fields are
    absent from CredentialForm entirely so the flag-OFF rendering is
    byte-identical to the legacy form.
    """
    from apps.accounts.forms.provider_request_wizard import CredentialForm

    request = RequestFactory().get("/")
    request.user = user

    form = CredentialForm(request=request)

    assert "fossil_free_energy_matching" not in form.fields
    assert "claim_coverage_percentage" not in form.fields


@pytest.mark.django_db
def test_credential_form_hides_matching_fields_when_request_is_none():
    """
    When no request is provided (defensive default), the matching fields
    are not surfaced regardless of any flag state.
    """
    from apps.accounts.forms.provider_request_wizard import CredentialForm

    form = CredentialForm()

    assert "fossil_free_energy_matching" not in form.fields
    assert "claim_coverage_percentage" not in form.fields


@pytest.mark.django_db
@override_flag("verification_basis_v2", active=True)
def test_credential_form_shows_matching_fields_when_flag_on(user):
    """
    With verification_basis_v2 ON, both new fields appear,
    fossil_free_energy_matching is required, claim_coverage_percentage is
    optional, and both sit immediately before ``description``.
    """
    from apps.accounts.forms.provider_request_wizard import CredentialForm

    request = RequestFactory().get("/")
    request.user = user

    form = CredentialForm(request=request)

    assert "fossil_free_energy_matching" in form.fields
    assert "claim_coverage_percentage" in form.fields
    assert form.fields["fossil_free_energy_matching"].required is True
    assert form.fields["claim_coverage_percentage"].required is False

    field_keys = list(form.fields.keys())
    assert field_keys.index("fossil_free_energy_matching") == field_keys.index("description") - 2
    assert field_keys.index("claim_coverage_percentage") == field_keys.index("description") - 1


@pytest.mark.django_db
@override_flag("verification_basis_v2", active=True)
def test_credential_form_matching_field_required_when_flag_on(user):
    """
    With the flag ON, omitting fossil_free_energy_matching invalidates the
    form; supplying a valid choice validates it (when other required fields
    are present).
    """
    from apps.accounts.forms.provider_request_wizard import CredentialForm

    request = RequestFactory().get("/")
    request.user = user

    required = {
        "type": models.EvidenceType.WEB_PAGE.value,
        "title": "Some title",
        "link": "https://example.com/evidence",
    }

    invalid_form = CredentialForm(
        data={
            **required,
            "public": False,
            # fossil_free_energy_matching deliberately omitted
            "claim_coverage_percentage": "",
        },
        request=request,
    )
    assert not invalid_form.is_valid()
    assert "fossil_free_energy_matching" in invalid_form.errors

    valid_form = CredentialForm(
        data={
            **required,
            "public": False,
            "fossil_free_energy_matching": models.FossilFreeEnergyMatching.ANNUAL.value,
            "claim_coverage_percentage": "",
        },
        request=request,
    )
    assert valid_form.is_valid(), valid_form.errors


@pytest.mark.django_db
@override_flag("verification_basis_v2", active=True)
def test_credential_form_coverage_percentage_optional_when_flag_on(user):
    """
    With the flag ON, claim_coverage_percentage remains optional: a form
    submitted without it is valid.
    """
    from apps.accounts.forms.provider_request_wizard import CredentialForm

    request = RequestFactory().get("/")
    request.user = user

    form = CredentialForm(
        data={
            "type": models.EvidenceType.WEB_PAGE.value,
            "title": "Some title",
            "link": "https://example.com/evidence",
            "public": False,
            "fossil_free_energy_matching": models.FossilFreeEnergyMatching.HOURLY.value,
            "claim_coverage_percentage": "",
        },
        request=request,
    )
    assert form.is_valid(), form.errors


@pytest.mark.django_db
@override_flag("verification_basis_v2", active=True)
@pytest.mark.parametrize(
    "value,should_be_valid",
    [
        (-1, False),
        (0, True),
        (100, True),
        (101, False),
    ],
)
def test_credential_form_coverage_percentage_bounds(user, value, should_be_valid):
    """
    claim_coverage_percentage is bounded to 0–100 via the form-field
    min/max_value validators.
    """
    from apps.accounts.forms.provider_request_wizard import CredentialForm

    request = RequestFactory().get("/")
    request.user = user

    form = CredentialForm(
        data={
            "type": models.EvidenceType.WEB_PAGE.value,
            "title": "Some title",
            "link": "https://example.com/evidence",
            "public": False,
            "fossil_free_energy_matching": models.FossilFreeEnergyMatching.ANNUAL.value,
            "claim_coverage_percentage": value,
        },
        request=request,
    )

    is_valid = form.is_valid()
    assert is_valid is should_be_valid, (
        f"expected valid={should_be_valid} for percentage={value}, "
        f"got valid={is_valid}, errors={form.errors}"
    )


# --- Wizard evidence step ---


def _walk_to_evidence_step(
    client, user, org_details, org_location, services
):
    """Walk through the wizard up to (and including) the services step."""
    client.force_login(user)
    client.post(urls.reverse("provider_registration"), org_details, follow=True)
    client.post(urls.reverse("provider_registration"), org_location, follow=True)
    client.post(urls.reverse("provider_registration"), services, follow=True)


@pytest.mark.django_db
@override_flag("verification_basis_v2", active=True)
def test_wizard_evidence_step_renders_new_fields_when_flag_on(
    user,
    client,
    wizard_form_org_details_data,
    wizard_form_org_location_data,
    wizard_form_services_data,
    wizard_form_verification_bases_data,
):
    """
    Given the verification_basis_v2 flag is ON, the green-evidence step
    surfaces the fossil_free_energy_matching and claim_coverage_percentage
    form fields immediately above the description textarea, and hides the
    legacy "avoid, reduce, or offset" intro sentence (superseded by the
    October 2026 criteria wording).
    """
    _walk_to_evidence_step(
        client,
        user,
        wizard_form_org_details_data,
        wizard_form_org_location_data,
        wizard_form_services_data,
    )

    # When the flag is ON, the basis form validates against the October
    # 2026 verification bases. Draw slugs from the flag-active choice set
    # so the basis step validates and the wizard advances to step "4".
    request = RequestFactory().get("/")
    request.user = user
    october_choices = models.ProviderRequest.get_verification_bases_choices(request)
    october_slugs = [slug for slug, _label in october_choices]
    bases_data = {
        "provider_request_wizard_view-current_step": "3",
        "3-verification_bases": october_slugs[:1],
    }

    response = client.post(
        urls.reverse("provider_registration"),
        bases_data,
        follow=True,
    )

    assert response.status_code == 200
    assert response.context_data["wizard"]["steps"].current == "4"

    content = response.content.decode()
    assert (
        "Does this disclosure support a claim of using annually, or hourly matched fossil-free energy?"
        in content
    )
    assert (
        "What percentage of your claims are met by this disclosure?"
        in content
    )
    # the legacy intro sentence is gated off when the flag is ON
    assert "avoid, reduce, or offset" not in content


@pytest.mark.django_db
def test_wizard_evidence_step_hides_new_fields_when_flag_off(
    user,
    client,
    wizard_form_org_details_data,
    wizard_form_org_location_data,
    wizard_form_services_data,
    wizard_form_verification_bases_data,
):
    """
    Given the verification_basis_v2 flag is OFF (the default), the
    green-evidence step does not surface the new field labels, and the
    legacy "avoid, reduce, or offset" intro sentence is still shown.
    """
    _walk_to_evidence_step(
        client,
        user,
        wizard_form_org_details_data,
        wizard_form_org_location_data,
        wizard_form_services_data,
    )

    response = client.post(
        urls.reverse("provider_registration"),
        wizard_form_verification_bases_data,
        follow=True,
    )

    assert response.status_code == 200
    assert response.context_data["wizard"]["steps"].current == "4"

    content = response.content.decode()
    assert (
        "Does this disclosure support a claim of using annually, or hourly matched fossil-free energy?"
        not in content
    )
    assert (
        "What percentage of your claims are met by this disclosure?"
        not in content
    )
    # the legacy intro sentence is shown when the flag is OFF
    assert "avoid, reduce, or offset" in content


# --- Preview step ---


@pytest.mark.django_db
@override_flag("verification_basis_v2", active=True)
def test_wizard_preview_renders_new_fields_when_flag_on(
    user,
    client,
    wizard_form_org_details_data,
    wizard_form_org_location_data,
    wizard_form_services_data,
    wizard_form_evidence_data_with_matching,
    wizard_form_network_explanation_only,
    wizard_form_consent,
):
    """
    Given the flag is ON and the evidence step is submitted with both new
    fields populated, the preview step renders the submitted values for
    each evidence row.
    """
    client.force_login(user)
    # When the flag is ON, the basis form validates against October 2026
    # verification bases; the default fixture draws June slugs which would
    # fail validation. Build the basis payload from the flag-active choices.
    request = RequestFactory().get("/")
    request.user = user
    october_choices = models.ProviderRequest.get_verification_bases_choices(request)
    october_slugs = [slug for slug, _label in october_choices]
    bases_data = {
        "provider_request_wizard_view-current_step": "3",
        "3-verification_bases": october_slugs[:1],
    }
    steps = [
        wizard_form_org_details_data,
        wizard_form_org_location_data,
        wizard_form_services_data,
        bases_data,
        wizard_form_evidence_data_with_matching,
        wizard_form_network_explanation_only,
        wizard_form_consent,
    ]
    for data in steps:
        response = client.post(urls.reverse("provider_registration"), data, follow=True)
        assert response.status_code == 200

    # the final POST above should have rendered the preview step
    assert response.context_data["wizard"]["steps"].current == "7"

    content = response.content.decode()
    # the selected matching value is echoed back as an option on the preview form
    assert models.FossilFreeEnergyMatching.ANNUAL.label in content or "Annually matched" in content
    assert "75" in content


@pytest.fixture()
def wizard_form_evidence_data_with_matching(fake_evidence):
    """
    Evidence step payload that populates the new matching and coverage
    fields for the first row, so the preview step has data to render.
    """
    return {
        "provider_request_wizard_view-current_step": "4",
        "4-TOTAL_FORMS": 2,
        "4-INITIAL_FORMS": 0,
        "4-0-title": " ".join(faker.words(3)),
        "4-0-link": faker.url(),
        "4-0-file": "",
        "4-0-type": models.EvidenceType.WEB_PAGE.value,
        "4-0-public": "on",
        "4-0-fossil_free_energy_matching": models.FossilFreeEnergyMatching.ANNUAL.value,
        "4-0-claim_coverage_percentage": "75",
        "4-1-title": " ".join(faker.words(3)),
        "4-1-link": "",
        "4-1-file": fake_evidence,
        "4-1-type": models.EvidenceType.ANNUAL_REPORT.value,
        "4-1-public": "on",
        "4-1-fossil_free_energy_matching": models.FossilFreeEnergyMatching.HOURLY.value,
        "4-1-claim_coverage_percentage": "50",
    }


# --- Approval ---


@freeze_time("Feb 15th, 2023")
@pytest.mark.django_db
def test_approve_copies_matching_and_coverage_to_supporting_document():
    """
    When a ProviderRequest carrying the new matching/coverage fields is
    approved, the resulting HostingProviderSupportingDocument carries the
    same values for both fields.
    """
    pr = ProviderRequestFactory.create()
    ProviderRequestLocationFactory.create(request=pr)

    ev = ProviderRequestEvidenceFactory.create(
        request=pr,
        fossil_free_energy_matching=models.FossilFreeEnergyMatching.HOURLY.value,
        claim_coverage_percentage=63,
    )

    result = pr.approve()
    hp = models.Hostingprovider.objects.get(id=result.id)

    persisted = hp.supporting_documents.filter(title=ev.title).get()
    assert persisted.fossil_free_energy_matching == models.FossilFreeEnergyMatching.HOURLY.value
    assert persisted.claim_coverage_percentage == 63


@freeze_time("Feb 15th, 2023")
@pytest.mark.django_db
def test_approve_copies_null_matching_and_coverage_when_absent():
    """
    When the new fields are unset (None), approve() still succeeds and
    the resulting HostingProviderSupportingDocument carries None for both.
    """
    pr = ProviderRequestFactory.create()
    ProviderRequestLocationFactory.create(request=pr)

    ev = ProviderRequestEvidenceFactory.create(
        request=pr,
        fossil_free_energy_matching=None,
        claim_coverage_percentage=None,
    )

    result = pr.approve()
    hp = models.Hostingprovider.objects.get(id=result.id)

    persisted = hp.supporting_documents.filter(title=ev.title).get()
    assert persisted.fossil_free_energy_matching is None
    assert persisted.claim_coverage_percentage is None


# --- Admin ---


@pytest.mark.django_db
def test_provider_request_evidence_inline_includes_new_fields():
    """
    The ProviderRequestEvidenceInline exposes both new fields so admins
    can review them when looking at a ProviderRequest.
    """
    from apps.accounts.admin.provider_request import ProviderRequestEvidenceInline

    inline_field_names = {f.name for f in ProviderRequestEvidenceInline.model._meta.fields}
    assert "fossil_free_energy_matching" in inline_field_names
    assert "claim_coverage_percentage" in inline_field_names
