import pytest
import io

from django import urls
from django.core.exceptions import ValidationError
from django.core.files import File
from waffle.testutils import override_flag

from .. import models


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
