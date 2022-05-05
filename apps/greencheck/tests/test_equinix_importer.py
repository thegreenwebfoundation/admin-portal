import pathlib

import pytest
from apps.greencheck import bulk_importers


@pytest.fixture
def equinix_list():
    return pathlib.Path("./apps/greencheck/tests/equinix.ips.and.asns..2022-02-25.txt")


class TestEquinixExporter:
    """
    Can we pull out the expected number of IP ranges and ASNs from the
    provided text file?
    """

    @pytest.mark.only
    def test_extracting_asns(self, db, hosting_provider_with_sample_user, equinix_list):
        """
        Pull out a list of ASNs we can represent in
        the system as GreenASNs
        """
        hosting_provider_with_sample_user.id

        equinix_importer = bulk_importers.ImporterEquinix()
        lines = equinix_importer.lines_from_file(equinix_list)

        asns = equinix_importer.parse_ASN(lines)

    def test_extracting_ipv4_ranges(self, equinix_list):
        """
        Pull out the list of IP v4 ranges converting the
        class ranges to fit our representation
        """
        pass

    def test_extracting_ipv6_ranges(self, equinix_list):
        """
        As above, but pull out the list of IP V6 ranges from
        the linesgit
        """
        pass
