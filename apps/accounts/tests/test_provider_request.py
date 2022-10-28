import pytest
import io
from django.core.exceptions import ValidationError
from django.core.files import File

from .. import models


@pytest.fixture
def mock_open(mocker):
    return mocker.patch("builtins.open")


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
    mock_open.return_value = io.StringIO("file contents")

    provider_request_location.save()
    evidence_data["location"] = provider_request_location

    evidence = models.ProviderRequestEvidence.objects.create(**evidence_data)

    with pytest.raises(ValidationError):
        evidence.full_clean()
