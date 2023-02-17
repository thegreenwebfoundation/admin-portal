import pytest
import io
import random

from django import urls
from django.core.exceptions import ValidationError
from django.core.files import File
from django.shortcuts import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from waffle.testutils import override_flag
from faker import Faker
from ipaddress import ip_address
from freezegun import freeze_time
from datetime import date

from conftest import (
    ProviderRequestFactory,
    ProviderRequestLocationFactory,
    ProviderRequestIPRangeFactory,
    ProviderRequestASNFactory,
    ProviderRequestEvidenceFactory,
)
from .. import views, models
from apps.greencheck.factories import TagFactory

faker = Faker()


@pytest.fixture()
def wizard_form_org_details_data():
    """
    Returns valid data for step ORG_DETAILS of the wizard
    as expected by the POST request.
    """
    return {
        "provider_registration_view-current_step": "0",
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
        "provider_registration_view-current_step": "1",
        "1-TOTAL_FORMS": "1",
        "1-INITIAL_FORMS": "0",
        "1-0-country": faker.country_code(),
        "1-0-city": faker.city(),
    }


@pytest.fixture()
def wizard_form_services_data():
    """
    Returns valid data for step SERVICES of the wizard
    as expected by the POST request.
    """
    for _ in range(5):
        TagFactory.create()

    tags_choices = models.Tag.objects.all()

    return {
        "provider_registration_view-current_step": "2",
        "2-services": random.sample([tag.slug for tag in tags_choices], 3),
    }


@pytest.fixture()
def wizard_form_evidence_data(fake_evidence):
    """
    Returns valid data for step GREEN_EVIDENCE of the wizard
    as expected by the POST request.
    """
    return {
        "provider_registration_view-current_step": "3",
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
        "provider_registration_view-current_step": "4",
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
def wizard_form_consent():
    """
    Returns valid data for step CONSENT of the wizard,
    as expected by the POST request.
    """
    return {
        "provider_registration_view-current_step": "5",
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
        "provider_registration_view-current_step": "6",
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
def test_list_view_displays_only_authored_requests(client):
    # given: 3 provider requests exist, created by different users
    pr1 = ProviderRequestFactory.create()
    pr2 = ProviderRequestFactory.create()
    pr3 = ProviderRequestFactory.create()

    # when: accessing the list view as the author of pr2
    client.force_login(pr2.created_by)
    response = client.get(urls.reverse("provider_request_list"))

    # then: link to detail view of pr2 is displayed
    assert response.status_code == 200
    assert f'href="{pr2.get_absolute_url()}"'.encode() in response.content

    # then: links to pr1 and pr3 are not displayed
    assert f'href="{pr1.get_absolute_url()}"'.encode() not in response.content
    assert f'href="{pr3.get_absolute_url()}"'.encode() not in response.content


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


def _create_provider_request(client, form_data):
    """
    Run through the steps the form wizard with the provided form data,
    to create a new provider request.
    """
    for step, data in enumerate(form_data, 1):
        response = client.post(urls.reverse("provider_registration"), data, follow=True)


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
    assert eml.subject == "Your verification request for the Green Web Database"
    assert (
        "Thank you for taking the time to complete a verification request"
        in msg_body_txt
    )
    assert (
        "Thank you for taking the time to complete a verification request"
        in msg_body_html
    )

    # then: and finally our email links back to the submission, contains the status, and the correct organisation
    provider_name = wizard_form_org_details_data["0-name"]
    provider_request = models.ProviderRequest.objects.get(name=provider_name)
    request_path = reverse("provider_request_detail", args=[provider_request.id])

    # should be something like http://testserver/requests/1/ ,
    # but more like https://app.greenweb/requests/1/ when live
    link_to_verification_request = f"http://testserver{request_path}"

    assert link_to_verification_request in msg_body_txt
    assert link_to_verification_request in msg_body_html

    assert provider_request.name in msg_body_txt
    assert provider_request.name in msg_body_html

    assert provider_request.status in msg_body_txt
    assert provider_request.status in msg_body_html


def test_approve_fails_when_hostingprovider_for_user_exists(db, user_with_provider):
    # given: provider request submitted by a user that already has a Hostingprovider assigned
    pr = ProviderRequestFactory.create(created_by=user_with_provider)
    existing_provider = user_with_provider.hostingprovider

    # then: approving the request fails
    with pytest.raises(ValueError):
        pr.approve()

    # then: user is still assigned to the old provider
    assert (
        models.User.objects.get(pk=user_with_provider.pk).hostingprovider
        == existing_provider
    )


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


def test_approve_first_location_is_persisted(db):
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


def test_approve_asn_already_exists(db, green_asn):
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
    assert models.User.objects.get(pk=pr.created_by.pk).hostingprovider is None
    assert models.Hostingprovider.objects.filter(request=pr).exists() is False


def test_approve_changes_status_to_approved(db):
    # given: a provider request is created
    pr = ProviderRequestFactory.create()
    ProviderRequestLocationFactory.create(request=pr)
    ProviderRequestEvidenceFactory.create(request=pr)

    # when: the request is approved
    pr.approve()

    # then: the request status is changed
    assert (
        models.ProviderRequest.objects.get(pk=pr.pk).status
        == models.ProviderRequestStatus.APPROVED
    )


def test_approve_creates_hosting_provider(db):
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


def test_approve_creates_ip_ranges(db):
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


def test_approve_creates_asns(db):
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
def test_approve_creates_evidence_documents(db):
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
