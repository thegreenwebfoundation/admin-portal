import pathlib

import pytest
from apps.greencheck import bulk_importers


@pytest.fixture
def equinix_list():
    return pathlib.Path("./apps/greencheck/tests/equinix.ips.and.asns.2022-02-25.txt")


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


# Sample code from a REPL session
# please assume this code is a starting point and probably doesn't work

# eq_path = pathlib.Path('./apps/greencheck/tests/equinix.ips.and.asns.2022-02-25.txt')

# create a variable we can refer to later
# eq_buf = None
# with open(eq_path) as eq_f:
#   eq_buf = eq_f.readlines()

# check the data looks like what we expect
# eq_buf[0]
# eq_buf[0].startswith(|"AS")

# use a pythonic lit comprehension to pull out lines starting with AS
# eq_asns = [line for line in eq_buf if line.startswith("AS")]

# fetch just the AS number from each line
# just_asns = [line.split('')[0] for line in eq_asns]
# eq_asns[0].split(' ')

# define a function to pull out the AS number from a line
# def fetch_asn(line):
#   broken_up = line.split(' ')
#   if broken_up:
#       return broken_up[0]

# test it out
# fetch_asn(eq_asns[0])

# built a list of the ASNs for import
#    for line in eq_asns:
#       res = fetch_asn(line)
#       if res:
#           just_asns.append(res)
