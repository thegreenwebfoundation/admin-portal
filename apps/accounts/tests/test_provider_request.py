import pytest
import io
import factory
import random

from django import urls
from django.core.exceptions import ValidationError
from django.core.files import File
from waffle.testutils import override_flag
from factory.django import DjangoModelFactory
from faker import Faker
from ipaddress import ip_address

from .. import views, models
from apps.greencheck.factories import UserFactory, TagFactory

faker = Faker()


class ProviderRequestFactory(DjangoModelFactory):
    name = factory.Faker("word")
    website = factory.Faker("domain_name")
    description = factory.Faker("sentence")
    status = models.ProviderRequestStatus.OPEN
    created_by = factory.SubFactory(UserFactory)
    services = factory.List([factory.SubFactory(TagFactory) for _ in range(3)])

    class Meta:
        model = models.ProviderRequest


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
        "0-country": faker.country_code(),
        "0-city": faker.city(),
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
        "provider_registration_view-current_step": "1",
        "1-services": random.sample([tag.slug for tag in tags_choices], 3),
    }


@pytest.fixture()
def wizard_form_evidence_data(fake_evidence):
    """
    Returns valid data for step GREEN_EVIDENCE of the wizard
    as expected by the POST request.
    """
    return {
        "provider_registration_view-current_step": "2",
        "2-TOTAL_FORMS": 2,
        "2-INITIAL_FORMS": 0,
        "2-0-title": " ".join(faker.words(3)),
        "2-0-link": faker.url(),
        "2-0-file": "",
        "2-0-type": models.EvidenceType.WEB_PAGE.value,
        "2-0-public": "on",
        "2-1-title": " ".join(faker.words(3)),
        "2-1-link": "",
        "2-1-file": fake_evidence,
        "2-1-type": models.EvidenceType.ANNUAL_REPORT.value,
        "2-1-public": "on",
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
        "provider_registration_view-current_step": "3",
        "ips__3-TOTAL_FORMS": "2",
        "ips__3-INITIAL_FORMS": "0",
        "ips__3-0-start": sorted_ips[0],
        "ips__3-0-end": sorted_ips[1],
        "ips__3-1-start": sorted_ips[2],
        "ips__3-1-end": sorted_ips[3],
        "asns__3-TOTAL_FORMS": "1",
        "asns__3-INITIAL_FORMS": "0",
        "asns__3-0-asn": faker.random_int(min=100, max=999),
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
    file.name = "evidence.txt"
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
def test_evidence_validation_fails(evidence_data, provider_request, mock_open):
    provider_request.save()
    evidence_data["request"] = provider_request

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
    wizard_form_services_data,
    wizard_form_evidence_data,
    wizard_form_network_data,
):

    # given: valid form data and authenticated user
    form_data = [
        wizard_form_org_details_data,
        wizard_form_services_data,
        wizard_form_evidence_data,
        wizard_form_network_data,
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
