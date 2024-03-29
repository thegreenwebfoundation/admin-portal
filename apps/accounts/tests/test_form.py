import logging
from ipaddress import ip_address

import pytest
from faker import Faker

from apps.accounts.forms import (
    GreenEvidenceForm,
    IpRangeForm,
    NetworkFootprintForm,
    LocationsFormSet,
    LocationStepForm,
)
from apps.accounts.models import EvidenceType
from apps.greencheck import forms as gc_forms
from apps.greencheck import models as gc_models

logger = logging.getLogger(__name__)
faker = Faker()


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


def test_green_evidence_form_validation():
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


def test_green_evidence_formset_invalid_when_empty():
    formset_data = {
        # management form data
        "form-TOTAL_FORMS": "0",
        "form-INITIAL_FORMS": "0",
    }
    formset = GreenEvidenceForm(data=formset_data)
    assert not formset.is_valid()


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


@pytest.fixture()
def wizard_form_network_import_required_only():
    """
    Returns valid data for step NETWORK_FOOTPRINT of the wizard
    as expected by the POST request.
    """
    return {
        "ips-TOTAL_FORMS": "0",
        "ips-INITIAL_FORMS": "0",
        "asns-TOTAL_FORMS": "0",
        "asns-INITIAL_FORMS": "0",
        "extra-network_import_required": "on",
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

    def test_form_valid_with_just_network_import_required(
        self, wizard_form_network_import_required_only
    ):
        """
        When we have no network data, but the user has marked that they have structured
        data to import
        """
        # given a valid submission
        multiform = NetworkFootprintForm(wizard_form_network_import_required_only)

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


def test_locations_formset_invalid_with_no_locations():
    """
    When we have no locations presented, our empty formset
    should be invalid.
    """
    # given an empty payload:
    empty_data = {
        "form-TOTAL_FORMS": "0",
        "form-INITIAL_FORMS": "0",
    }

    formset = LocationsFormSet(empty_data)

    # then our form should be invalid
    assert not formset.is_valid()


def test_location_step_form_when_invalid_raises_errors():
    """
    Check that non field errors are raised from a formset to a multiform.

    By default, multimodelforms do not seem to correctly raise errors on
    formsets
    """
    # given an empty formset
    empty_data = {
        "form-TOTAL_FORMS": "0",
        "form-INITIAL_FORMS": "0",
    }

    step_form = LocationStepForm(empty_data)

    # then our form should not show as valid
    assert not step_form.is_valid()

    # and our error list should show tell us that we are missing the necessary
    # location sub-form submission
    assert "Please submit at least 1 location." in step_form.non_field_errors()


def test_location_step_empty_form_bulk_import_selected():
    # given an empty formset with the bulk import option selected
    empty_data = {
        "form-TOTAL_FORMS": "0",
        "form-INITIAL_FORMS": "0",
        "extra-location_import_required": "on",
    }

    step_form = LocationStepForm(empty_data)

    # then form is not valid
    assert not step_form.is_valid()
    assert (
        "You've selected the bulk import option, but we still need to know where your headquarters are. Please submit at least 1 location."
        in step_form.non_field_errors()
    )


def test_evidence_formset_empty():
    empty_data = {
        "form-TOTAL_FORMS": "0",
        "form-INITIAL_FORMS": "0",
    }

    evidence_formset = GreenEvidenceForm(empty_data)
    assert evidence_formset.is_valid() is False
    assert any(
        "Please submit at least one row of evidence" in error_msg
        for error_msg in evidence_formset.non_form_errors()
    )
