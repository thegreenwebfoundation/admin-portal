import pytest
import io

from django import urls
from django.core.exceptions import ValidationError
from django.core.files import File

from .. import models


@pytest.fixture
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
def test_provider_request_evidence_validation_fails(
    evidence_data, provider_request_location, mock_open
):
    provider_request_location.save()
    evidence_data["location"] = provider_request_location

    evidence = models.ProviderRequestEvidence.objects.create(**evidence_data)

    with pytest.raises(ValidationError):
        evidence.full_clean()


@pytest.mark.django_db
def test_provider_request_admin_regular_user_cannot_access(sample_hoster_user, client):
    client.force_login(sample_hoster_user)
    admin_url = urls.reverse("greenweb_admin:accounts_providerrequest_changelist")

    response = client.get(admin_url)

    assert response.status_code == 403


@pytest.mark.django_db
def test_provider_request_admin_staff_user_can_access(greenweb_staff_user, client):
    client.force_login(greenweb_staff_user)
    admin_url = urls.reverse("greenweb_admin:accounts_providerrequest_changelist")

    response = client.get(admin_url)

    assert response.status_code == 200
