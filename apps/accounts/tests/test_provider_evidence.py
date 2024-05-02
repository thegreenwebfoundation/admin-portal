import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from faker import Faker
from ..factories import (
    ProviderRequestFactory,
    SupportingEvidenceFactory,
    ProviderRequestEvidenceFactory,
)

faker = Faker()
initial_evidence_description = faker.text().encode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "file_content,check_result",
    [(initial_evidence_description, True), (faker.text().encode(), False)],
)
def test_evidence_has_content_match(
    hosting_provider_with_sample_user, file_content, check_result
):
    """
    Check that for a item of evidence, we can check it against
    existing supporting documents to see if there is a match
    """

    provider = hosting_provider_with_sample_user
    pr = ProviderRequestFactory.create(provider=provider)

    initial_evidence_upload = SimpleUploadedFile(
        name=faker.file_name(), content=file_content
    )
    provider_evidence = SupportingEvidenceFactory.create(
        attachment=initial_evidence_upload,
        type="Annual Report",
        hostingprovider=hosting_provider_with_sample_user,
        public=True,
    )

    vf_evidence = ProviderRequestEvidenceFactory.create(
        request=pr,
        link=None,
        title=provider_evidence.title,
        type=provider_evidence.type,
        public=provider_evidence.public,
        file=SimpleUploadedFile(
            name=faker.file_name(), content=initial_evidence_description
        ),
    )
    assert vf_evidence.has_content_match(provider_evidence) is check_result


@pytest.mark.django_db
def test_evidence_has_content_match_works_checking_attachment_against_url(
    hosting_provider_with_sample_user,
):
    """
    Check that for a item of evidence with , when we check agains
    """

    provider = hosting_provider_with_sample_user
    pr = ProviderRequestFactory.create(provider=provider)

    initial_evidence_upload = SimpleUploadedFile(
        name=faker.file_name(), content=initial_evidence_description
    )
    provider_evidence = SupportingEvidenceFactory.create(
        attachment=initial_evidence_upload,
        type="Annual Report",
        hostingprovider=hosting_provider_with_sample_user,
        public=True,
    )

    vf_evidence = ProviderRequestEvidenceFactory.create(
        request=pr,
        link=faker.url(),
        title=provider_evidence.title,
        type=provider_evidence.type,
        public=provider_evidence.public,
    )
    assert vf_evidence.has_content_match(provider_evidence) is False


@pytest.mark.django_db
def test_evidence_has_content_match_works_checking_url_against_attachment(
    hosting_provider_with_sample_user,
):
    provider = hosting_provider_with_sample_user
    pr = ProviderRequestFactory.create(provider=provider)

    initial_evidence_upload = SimpleUploadedFile(
        name=faker.file_name(), content=initial_evidence_description
    )
    provider_evidence = SupportingEvidenceFactory.create(
        type="Annual Report",
        hostingprovider=hosting_provider_with_sample_user,
        public=True,
    )

    vf_evidence = ProviderRequestEvidenceFactory.create(
        request=pr,
        file=initial_evidence_upload,
        title=provider_evidence.title,
        type=provider_evidence.type,
        public=provider_evidence.public,
    )
    assert vf_evidence.has_content_match(provider_evidence) is False
