import pytest

from apps.greencheck.exceptions import NoMatchingDomainHash
from apps.greencheck.models import GreenDomain


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

        def test_claim_domain_with_via_header(self):
            """
            Test that claiming a domain with a valid domain hash in the 'via header'
            is successful.
            """

            pass
