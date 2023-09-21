import pytest
import io
import random

from django import urls
from django.core.exceptions import ValidationError
from django.core.files import File
from django.shortcuts import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from waffle.testutils import override_flag
from faker import Faker
from ipaddress import ip_address
from freezegun import freeze_time
from datetime import date, datetime

from conftest import (
    ProviderRequestFactory,
    ProviderRequestLocationFactory,
    ProviderRequestIPRangeFactory,
    ProviderRequestASNFactory,
    ProviderRequestEvidenceFactory,
)
from .. import views, models
from apps.greencheck.factories import ServiceFactory

from django.conf import settings

faker = Faker()


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
def wizard_form_evidence_data(fake_evidence):
    """
    Returns valid data for step GREEN_EVIDENCE of the wizard
    as expected by the POST request.
    """
    return {
        "provider_request_wizard_view-current_step": "3",
        "3-TOTAL_FORMS": 2,
        "3-INITIAL_FORMS": 0,
        "3-0-title": " ".join(faker.words(3)),
        "3-0-link": faker.url(),
        "3-0-file": "",
        "3-0-type": models.EvidenceType.WEB_PAGE.value,
        "3-0-public": "on",
        "3-1-title": " ".join(faker.words(3)),
        "3-1-link": "",
        "3-1-file": fake_evidence,
        "3-1-type": models.EvidenceType.ANNUAL_REPORT.value,
        "3-1-public": "on",
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
        "provider_request_wizard_view-current_step": "4",
        "ips__4-TOTAL_FORMS": "2",
        "ips__4-INITIAL_FORMS": "0",
        "ips__4-0-start": sorted_ips[0],
        "ips__4-0-end": sorted_ips[1],
        "ips__4-1-start": sorted_ips[2],
        "ips__4-1-end": sorted_ips[3],
        "asns__4-TOTAL_FORMS": "1",
        "asns__4-INITIAL_FORMS": "0",
        "asns__4-0-asn": faker.random_int(min=100, max=999),
    }


@pytest.fixture()
def wizard_form_network_explanation_only():
    """
    Returns valid explanation for step NETWORK_FOOTPRINT of the
    form wizard, without any IP or AS information.
    """
    return {
        "provider_request_wizard_view-current_step": "4",
        "ips__4-TOTAL_FORMS": "0",
        "ips__4-INITIAL_FORMS": "0",
        "asns__4-TOTAL_FORMS": "0",
        "asns__4-INITIAL_FORMS": "0",
        "extra__4-missing_network_explanation": faker.sentence(10),
    }


@pytest.fixture()
def wizard_form_consent():
    """
    Returns valid data for step CONSENT of the wizard,
    as expected by the POST request.
    """
    return {
        "provider_request_wizard_view-current_step": "5",
        "5-data_processing_opt_in": "on",
        "5-newsletter_opt_in": "off",
    }


@pytest.fixture()
def wizard_form_preview():
    """
    Returns valid data for step PREVIEW of the wizard,
    as expected by the POST request.
    """
    return {
        "provider_request_wizard_view-current_step": "6",
    }


@pytest.fixture()
def mock_open(mocker):
    file_mock = mocker.patch("builtins.open")
    file_mock.return_value = io.StringIO("file contents")
    return file_mock


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
            "file": File(file="cert.pdf"),
            "type": models.EvidenceType.CERTIFICATE,
        },
        {
            "title": "this one has neither link nor file",
            "type": models.EvidenceType.CERTIFICATE,
        },
    ],
    ids=["both_file_and_link", "neither_file_nor_link"],
)
def test_evidence_validation_fails(evidence_data, mock_open):
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
@override_flag("provider_request", active=True)
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
@override_flag("provider_request", active=True)
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
@override_flag("provider_request", active=True)
def test_detail_view_forbidden_for_others(client, user):
    # given: provider request exists
    pr = ProviderRequestFactory.create()

    # when: accessing its detail view by another user
    client.force_login(user)
    response = client.get(urls.reverse("provider_request_detail", args=[str(pr.id)]))

    # then: page is not accessible
    assert response.status_code == 404


@pytest.mark.django_db
@override_flag("provider_request", active=True)
def test_wizard_view_happy_path(
    user,
    client,
    wizard_form_org_details_data,
    wizard_form_org_location_data,
    wizard_form_services_data,
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
@override_flag("provider_request", active=True)
def test_wizard_sends_email_on_submission(
    user,
    client,
    wizard_form_org_details_data,
    wizard_form_org_location_data,
    wizard_form_services_data,
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
    assert "support@thegreenwebfoundation.org" in eml.cc

    # then: and our email has the subject and copy we were expecting
    assert "Your verification request for the Green Web Database" in eml.subject

    assert (
        "Thank you for taking the time to complete a verification request"
        in msg_body_txt
    )
    assert (
        "Thank you for taking the time to complete a verification request"
        in msg_body_html
    )

    # then: and our email includes a BCC address so we can track status in
    # trello via sending a message to the email-to-board address
    assert settings.TRELLO_REGISTRATION_EMAIL_TO_BOARD_ADDRESS in eml.bcc

    # then: and finally our email links back to the submission, contains the status,
    # and the correct organisation
    provider_name = wizard_form_org_details_data["0-name"]
    provider_request = models.ProviderRequest.objects.get(name=provider_name)
    request_path = reverse("provider_request_detail", args=[provider_request.id])

    link_to_verification_request = f"http://testserver{request_path}"

    assert provider_name in eml.subject
    assert link_to_verification_request in msg_body_txt
    assert link_to_verification_request in msg_body_html

    assert provider_request.name in msg_body_txt
    assert provider_request.name in msg_body_html

    assert provider_request.status in msg_body_txt
    assert provider_request.status in msg_body_html


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
    pr = ProviderRequestFactory.create(services=faker.words(nb=4))
    ProviderRequestLocationFactory.create(request=pr)
    ProviderRequestEvidenceFactory.create(request=pr)

    # when: the request is approved
    result = pr.approve()
    hp = models.Hostingprovider.objects.get(id=result.id)

    # then: resulting Hostingprovider is configured properly
    assert hp.name == pr.name
    assert hp.description == pr.description
    assert list(hp.services.all()) == list(pr.services.all())
    assert hp.website == pr.website
    assert hp.request == pr
    assert hp.created_by == pr.created_by
    # then: user who created the request has permissions to manage the new hosting provider
    assert hp in pr.created_by.hosting_providers

    # provider is visible by default
    # appropriate tag is added
    assert hp.showonwebsite is True
    assert "up-to-date" in hp.staff_labels.slugs()
    # "other-none" is the label condition check for
    # when someone is just trying to get a site marked
    # as green when they don't offer hosted services
    assert "other-none" not in hp.services.slugs()


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
    assert hp.showonwebsite is False
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


@pytest.mark.django_db
@override_flag("provider_request", active=True)
def test_wizard_view_with_just_network_explanation(
    user,
    client,
    wizard_form_org_details_data,
    wizard_form_org_location_data,
    wizard_form_services_data,
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
        "extra__4-missing_network_explanation"
    )

    assert pr.missing_network_explanation == explanation
    assert pr_from_db.missing_network_explanation == explanation


@pytest.mark.django_db
@override_flag("provider_request", active=True)
def test_wizard_records_if_location_import_needed(
    user,
    client,
    wizard_form_org_details_data,
    wizard_form_org_location_data,
    wizard_form_services_data,
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
@override_flag("provider_request", active=True)
def test_new_submission_doesnt_modify_available_services(
    user,
    client,
    wizard_form_org_details_data,
    wizard_form_org_location_data,
    wizard_form_services_data,
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
@override_flag("provider_request", active=True)
def test_edit_view_accessible_by_creator(client):
    # given: an open provider request
    pr = ProviderRequestFactory.create()

    # when: accessing its edit view by the creator
    client.force_login(pr.created_by)
    response = client.get(urls.reverse("provider_request_edit", args=[str(pr.id)]))

    # then: page for the correct provider request is rendered
    assert response.status_code == 200


@pytest.mark.django_db
@override_flag("provider_request", active=True)
def test_edit_view_accessible_by_admin(client, greenweb_staff_user):
    # given: an open provider request
    pr = ProviderRequestFactory.create()

    # when: accessing its edit view by Green Web staff
    client.force_login(greenweb_staff_user)
    response = client.get(urls.reverse("provider_request_edit", args=[str(pr.id)]))

    # then: page for the correct provider request is rendered
    assert response.status_code == 200


@pytest.mark.django_db
@override_flag("provider_request", active=True)
def test_edit_view_inaccessible_by_other_users(client, user):
    # given: an open provider request
    pr = ProviderRequestFactory.create()

    # when: accessing its edit view by regular users other than the creator
    client.force_login(user)
    response = client.get(urls.reverse("provider_request_edit", args=[str(pr.id)]))

    # then: we pretend this request does not exist and show 404
    assert response.status_code == 404


@pytest.mark.django_db
@override_flag("provider_request", active=True)
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
@override_flag("provider_request", active=True)
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
@override_flag("provider_request", active=True)
def test_editing_pr_updates_original_submission(
    client,
    wizard_form_org_details_data,
    wizard_form_services_data,
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
