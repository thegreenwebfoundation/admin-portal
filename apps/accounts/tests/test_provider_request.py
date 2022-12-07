import pytest
import io
import factory

from django import urls
from django.core.exceptions import ValidationError
from django.core.files import File
from waffle.testutils import override_flag
from factory.django import DjangoModelFactory

from .. import models
from apps.greencheck.factories import UserFactory, TagFactory


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
def mock_open(mocker):
    file_mock = mocker.patch("builtins.open")
    file_mock.return_value = io.StringIO("file contents")
    return file_mock


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
def test_detail_view_accessible_by_creator(user, provider_request, client):
    provider_request.created_by = user
    provider_request.save()
    client.force_login(user)

    url = urls.reverse("provider_request_detail", args=[str(provider_request.id)])
    response = client.get(url)

    assert response.status_code == 200


@pytest.mark.django_db
@override_flag("provider_request", active=True)
def test_detail_view_forbidden_for_others(
    user, sample_hoster_user, provider_request, client
):
    provider_request.created_by = user
    provider_request.save()
    client.force_login(sample_hoster_user)

    url = urls.reverse("provider_request_detail", args=[str(provider_request.id)])
    response = client.get(url)

    assert response.status_code == 404


@pytest.mark.django_db
@override_flag("provider_request", active=True)
def test_list_view_displays_only_authored_requests(client):
    # given: 3 provider requests exist, created by different users
    pr1 = ProviderRequestFactory.create()
    pr2 = ProviderRequestFactory.create()
    pr3 = ProviderRequestFactory.create()

    # when: accessing the list view as the author of pr2
    user = pr2.created_by
    client.force_login(user)
    url = urls.reverse("provider_request_list")
    response = client.get(url)

    # then: link to detail view of pr2 is displayed
    assert response.status_code == 200
    assert f'href="{pr2.get_absolute_url()}"'.encode() in response.content

    # then: links to pr1 and pr3 are not displayed
    assert f'href="{pr1.get_absolute_url()}"'.encode() not in response.content
    assert f'href="{pr3.get_absolute_url()}"'.encode() not in response.content


@pytest.mark.django_db
@override_flag("provider_request", active=True)
def test_wizard_view_happy_path(user, client):
    # reference: https://marcosschroh.github.io/posts/testing-a-form-wizard-in-django/
    pass
