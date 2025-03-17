import pytest

from apps.greencheck.exceptions import NoMatchingDomainHash
from apps.greencheck.models import GreenDomain
from apps.accounts.models import DomainHash
from pytest_httpx import HTTPXMock


class TestGreenDomainClaim:
    """
    This code exercises the "domain claim" functionality in the platform, for
    carrying out a carbon.txt domain validation.
    """

    @pytest.mark.django_db
    class TestGreenDomainClaim:
        """
        This code exercises the "domain claim" functionality in the platform, for
        carrying out a carbon.txt domain validation.
        """

        def test_claim_domain_with_no_domain_hash(self):
            """
            Test that attempting to claim a domain without a corresponding domain hash
            raises a NoMatchingDomainHash exception.
            """
            domain_name = "example.com"

            with pytest.raises(NoMatchingDomainHash):
                GreenDomain.claim_via_carbon_txt(domain_name)

        def test_claim_domain_with_via_header(self, user_with_provider, httpx_mock):
            """
            Test that claiming a domain with a valid domain hash in the 'via header'
            is successful.
            """

            managed_service = "managed-service.com"
            hosted_site = "example.com"

            provider = user_with_provider.hosting_providers.first()
            provider.refresh_shared_secret()

            domain_hash = provider.create_domain_hash(hosted_site, user_with_provider)

            httpx_mock.add_response(
                url=f"https://example.com/carbon.txt",
                headers={"Via": f"{managed_service}/carbon.txt {domain_hash.hash}"},
            )

            resp = GreenDomain.claim_via_carbon_txt(hosted_site)

            assert resp in GreenDomain.objects.filter(hosted_by_id=provider.id)
