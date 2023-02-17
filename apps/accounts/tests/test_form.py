import logging
from ipaddress import ip_address

import io

import pytest
from apps.greencheck import forms as gc_forms
from apps.greencheck import models as gc_models
from apps.accounts.forms import (
    GreenEvidenceForm,
    IpRangeForm,
    LocationsForm,
    LocationForm,
    CredentialForm,
)
from apps.accounts.models import EvidenceType

from django.core.files.uploadedfile import SimpleUploadedFile

from faker import Faker

from apps.accounts.forms import GreenEvidenceForm, IpRangeForm, NetworkFootprintForm
from apps.accounts.models import EvidenceType
from apps.greencheck import forms as gc_forms
from apps.greencheck import models as gc_models

logger = logging.getLogger(__name__)

faker = Faker()


@pytest.mark.parametrize(
    "form_data",
    [
        {
            "start": "127.0.0.100",
            "end": "127.0.0.1",
        },
        {
            "start": "127.0.0.100",
            "end": "this one is not a valid IP address",
        },
        {
            "start": "127.0.0.3/32",
            "end": "127.0.0.100",
        },
    ],
    ids=["end_before_start", "invalid_range_end", "invalid_range_start"],
)
def test_ip_range_form_validation(form_data):
    # when: the form is instantiated with invalid data
    ip_form = IpRangeForm(data=form_data)

    # then: the form is invalid
    assert ip_form.is_valid() is False


@pytest.fixture()
def sorted_ips():
    """
    Returns a list of fake IPv4 addresses, sorted in ascending order
    """
    return sorted([faker.ipv4() for _ in range(10)], key=lambda x: ip_address(x))


@pytest.fixture()
def wizard_form_network_data(sorted_ips):
    """
    Returns valid data for step NETWORK_FOOTPRINT of the wizard
    as expected by the POST request.
    """
    return {
        "ips-TOTAL_FORMS": "2",
        "ips-INITIAL_FORMS": "0",
        "ips-0-start": sorted_ips[0],
        "ips-0-end": sorted_ips[1],
        "ips-1-start": sorted_ips[2],
        "ips-1-end": sorted_ips[3],
        "asns-TOTAL_FORMS": "1",
        "asns-INITIAL_FORMS": "0",
        "asns-0-asn": faker.random_int(min=100, max=999),
    }


@pytest.fixture()
def wizard_form_empty_network_data():
    """
    Returns a form payload to simulate someone adding neither network info
    nor any explanation
    """
    return {
        "ips-TOTAL_FORMS": "0",
        "ips-INITIAL_FORMS": "0",
        "asns-TOTAL_FORMS": "0",
        "asns-INITIAL_FORMS": "0",
        "extra-missing_network_explanation": "",
    }


def fake_evidence():
    """
    Returns a file-like object with fake content
    """
    file = io.BytesIO(faker.text().encode())
    file.name = "evidence.txt"
    return file


@pytest.fixture()
def wizard_form_evidence_data():
    """
    Returns valid data for step GREEN_EVIDENCE of the wizard
    as expected by the POST request.
    """
    return {
        "form-TOTAL_FORMS": 1,
        "form-INITIAL_FORMS": 0,
        "form-0-title": " ".join(faker.words(3)),
        "form-0-link": faker.url(),
        "form-0-file": "",
        "form-0-type": EvidenceType.WEB_PAGE.value,
        "form-0-public": "on",
        "form-0-description": "",
    }


@pytest.fixture()
def wizard_form_network_explanation_only():
    """
    Returns valid data for step NETWORK_FOOTPRINT of the wizard
    as expected by the POST request.
    """
    return {
        "ips-TOTAL_FORMS": "0",
        "ips-INITIAL_FORMS": "0",
        "asns-TOTAL_FORMS": "0",
        "asns-INITIAL_FORMS": "0",
        "extra-missing_network_explanation": "Some information",
    }


def wizard_form_org_location_data():
    """
    Returns valid data for the step ORG_LOCATIONS of the wizard,
    as expected by the POST request.
    """
    city_name = faker.city()

    return {
        "form-TOTAL_FORMS": "1",
        "form-INITIAL_FORMS": "0",
        "form-0-name": city_name,
        "form-0-country": faker.country_code(),
        "form-0-city": city_name,
    }


class TestGreencheckIpForm:
    def test_approve_ip_range_fails_without_change_attribute_set(
        self, db, hosting_provider
    ):
        """
        Check that we at least raise a sensible error when we do not have
        the "changed" attribute set on the form.

        This tests we are using our hack, but also demonstrates the intended usage,
        simulating what we are doing in the admin.
        """
        hosting_provider.save()
        form = gc_forms.GreencheckIpForm(
            {"active": True, "ip_start": "169.145.4.1", "ip_end": "169.145.4.2"},
        )

        with pytest.raises(gc_forms.ChangeStateRequiredError):
            form.save()

    def test_approve_ip_range_with_change_attribute_set(self, db, hosting_provider):
        """
        Check that we can accept a submitted IP range, via the form, but
        create a request to approve the range, instead of blindly creating it.
        """
        hosting_provider.save()

        # to simulate being used in an admin form, we create a a partial instance,
        # with the values not set by the form and pass it in
        partial_green_ip = gc_models.GreencheckIp(hostingprovider=hosting_provider)

        form = gc_forms.GreencheckIpForm(
            {
                "active": True,
                "ip_start": "169.145.4.1",
                "ip_end": "169.145.4.2",
                "is_staff": False,
            },
            instance=partial_green_ip,
        )

        # setting changed here is what we do in our admin hack. this simulates the form
        # being used in an admin context where we are using the same `changed = True/False` hack
        form.changed = True
        assert form.is_valid()

        form.save()

        # have we created an approval request, instead of an IP?
        assert gc_models.GreencheckIpApprove.objects.count() == 1
        assert gc_models.GreencheckIp.objects.count() == 0

    def test_approve_ip_range_with_change_attribute_set_as_staff(
        self, db, hosting_provider
    ):
        """
        Check that we can accept a submitted IP range, via the form,
        and create it directly when submitted by a member of staff.
        """
        hosting_provider.save()
        partial_green_ip = gc_models.GreencheckIp(hostingprovider=hosting_provider)

        form = gc_forms.GreencheckIpForm(
            {
                "active": True,
                "ip_start": "169.145.4.1",
                "ip_end": "169.145.4.2",
                "is_staff": True,
            },
            instance=partial_green_ip,
        )
        form.changed = True
        assert form.is_valid()

        form.save()

        # have we created an actual green IP, and skipped the approval lifecycle?
        assert gc_models.GreencheckIp.objects.count() == 1


class TestNetworkFootprintForm:
    def test_form_valid_with_network_address_info_no_explanation(
        self, wizard_form_network_data
    ):
        """
        When we have network data but no explanationm count it as valid.
        """

        # given a valid submission
        multiform = NetworkFootprintForm(wizard_form_network_data)

        # then our form should be valid
        assert multiform.is_valid()

    def test_form_valid_with_just_explanation(
        self, wizard_form_network_explanation_only
    ):
        """
        When we have no network data, but some explanation, count it as valid.
        """

        # given a valid submission
        multiform = NetworkFootprintForm(wizard_form_network_explanation_only)

        # then our form should be valid
        assert multiform.is_valid()

    def test_form_not_valid_if_no_explanation_or_network_data(
        self, wizard_form_empty_network_data
    ):
        """
        When we have no information provided about the  network
        or an explanation, raise a meaningful error
        """

        # given a invalid submission
        multiform = NetworkFootprintForm(wizard_form_empty_network_data)

        # when: a validation check has been run
        validation_result = multiform.is_valid()

        # then: our form should not be valid
        assert validation_result is False

        # and: we should have the appropriate error
        form_errors = multiform.errors["__all__"]
        assert len(form_errors) > 0
        assert "no_network_no_explanation" in [error.code for error in form_errors]


class TestCredentialForm:
    def test_invalid_empty_credential_form(self):
        empty_data = {
            "link": "",
            "file": "",
            "type": "",
            "public": "",
            "title": "",
            "description": "",
        }

        form = CredentialForm(empty_data)
        valid_result = form.is_valid()
        assert not valid_result

    def test_valid_with_webpage_credential(self):
        valid_page_data = {
            "link": faker.url(),
            "file": "",
            "type": EvidenceType.WEB_PAGE.value,
            "public": "on",
            "title": " ".join(faker.words(3)),
            "description": "",
        }

        form = CredentialForm(valid_page_data)
        valid_result = form.is_valid()
        assert valid_result

    def test_valid_with_file_credential(self, fake_evidence):
        valid_uploaded_doc_data = {
            "link": "",
            "type": EvidenceType.ANNUAL_REPORT.value,
            "public": "on",
            "title": " ".join(faker.words(3)),
            "description": "",
        }
        file_data = {
            "file": SimpleUploadedFile(fake_evidence.name, fake_evidence.read())
        }

        form = CredentialForm(valid_uploaded_doc_data, file_data)
        valid_result = form.is_valid()
        assert valid_result

    def test_valid_with_file_credential(self, fake_evidence):
        valid_uploaded_doc_data = {
            "link": faker.url(),
            "type": EvidenceType.ANNUAL_REPORT.value,
            "public": "on",
            "title": " ".join(faker.words(3)),
            "description": "",
        }
        file_data = {
            "file": SimpleUploadedFile(fake_evidence.name, fake_evidence.read())
        }
        form = CredentialForm(valid_uploaded_doc_data, file_data)
        valid_result = form.is_valid()

        assert not valid_result


class TestGreenEvidenceForm:
    """
    Tests our bformset,
    """

    def test_valid_with_evidence(self, wizard_form_evidence_data):
        # given a valid submission
        formset = GreenEvidenceForm(wizard_form_evidence_data)

        assert formset.is_valid()

    def test_invalid_with_no_evidence(self):
        """
        When we have no presented evidence at all, our empty form should
        be invalid
        """

        empty_data = {
            "form-TOTAL_FORMS": 0,
            "form-INITIAL_FORMS": 0,
            "form-0-link": "",
            "form-0-type": "",
            "form-0-public": "",
            "form-0-title": "",
            "form-0-description": "",
        }

        # given an empty submission
        formset = GreenEvidenceForm(empty_data)

        # our formset should be invalid and we have a helpful error
        assert not formset.is_valid()
        assert "There needs to be at least one submission" in formset.non_form_errors()

    def test_green_evidence_form_validation(self):
        # given: invalid form data
        fake_title = " ".join(faker.words(3))
        fake_url = faker.url()
        formset_data = {
            # management form data
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "0",
            # 1st form is valid
            "form-0-title": fake_title,
            "form-0-link": fake_url,
            "form-0-file": "",
            "form-0-type": EvidenceType.WEB_PAGE.value,
            "form-0-public": "on",
            # 2nd form is missing: type, file, link
            "form-1-title": " ".join(faker.words(3)),
            "form-1-link": "",
            "form-1-file": "",
            "form-1-type": "",
            "form-1-public": "on",
            # 3rd form is identical to 1st
            "form-2-title": fake_title,
            "form-2-link": fake_url,
            "form-2-file": "",
            "form-2-type": EvidenceType.WEB_PAGE.value,
            "form-2-public": "on",
            # 4th form is empty
            "form-3-title": "",
            "form-3-link": "",
            "form-3-file": "",
            "form-3-type": "",
            "form-3-public": "on",
        }

        # when: the formset is instantiated and validation is performed
        formset = GreenEvidenceForm(data=formset_data)
        formset.full_clean()

        # then: first form is valid
        assert formset.forms[0].is_valid()
        # then: 2nd form has a field error (type is empty) and a non-field error (either file or link is required)
        assert formset.forms[1].has_error(field="type")
        assert len(formset.forms[1].non_field_errors()) == 1
        # then: 3rd form has a non-field error (duplicated data)
        assert len(formset.forms[2].non_field_errors()) == 1
        # then: 4th form has a non-field error (empty form)
        assert len(formset.forms[3].non_field_errors()) == 1
        # then: the whole formset is invalid
        assert not formset.is_valid()


class TestLocationForm:
    """
    Individual validation tests.
    """

    def test_valid_with_full_location(self):
        valid_location_data = {
            "name": "HQ",
            "country": faker.country_code(),
            "city": faker.city(),
        }
        form = LocationForm(valid_location_data)

        assert form.is_valid()

    def test_valid_without_name(self):
        valid_location_data = {
            "country": faker.country_code(),
            "city": faker.city(),
        }
        form = LocationForm(valid_location_data)

        assert form.is_valid()


class TestLocationsForm:
    """
    Test that our evidence form step checks for at least one piece
    of valid evidence exists - not just that the pieces of evidence
    are themselves valid.
    """

    def test_valid_with_evidence(self, wizard_form_org_location_data):
        """
        When we have one location our form should be valid
        """
        # given a valid submission
        formset = LocationsForm(wizard_form_org_location_data)
        # then our form should be valid
        assert formset.is_valid()

    def test_invalid_with_no_locations(self):
        """
        When we have no locations presented, our empty form should
        be invalid.
        """
        # given an empty payload:
        empty_data = {
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
        }

        formset = LocationsForm(empty_data)
        # then our form should be invalid
        assert not formset.is_valid()
