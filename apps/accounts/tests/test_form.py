import logging

import pytest
from apps.greencheck import forms as gc_forms
from apps.greencheck import models as gc_models
from apps.accounts.forms import GreenEvidenceForm
from apps.accounts.models import EvidenceType

from faker import Faker


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
