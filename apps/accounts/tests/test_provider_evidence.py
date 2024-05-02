import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from faker import Faker
from ..factories import (
    ProviderRequestFactory,
    SupportingEvidenceFactory,
    ProviderRequestEvidenceFactory,
    ProviderRequestLocationFactory,
)

faker = Faker()
initial_evidence_description = faker.text().encode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "file_content,check_result",
    [(initial_evidence_description, True), (faker.text().encode(), False)],
)
def test_evidence_is_duplicate_upload(
    hosting_provider_with_sample_user, file_content, check_result
):
    """
    Check that for a item of evidence, we can check it against
    existing supporting documents to see if there is a match
    """

    provider = hosting_provider_with_sample_user
    pr = ProviderRequestFactory.create(provider=provider)
    # ProviderRequestLocationFactory.create(request=pr)

    # # and: a piece of evidence that is already associated with the provider

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
    assert vf_evidence.is_duplicate_upload(provider_evidence) is check_result
