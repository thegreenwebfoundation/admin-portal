import logging

import pytest
from apps.greencheck import forms as gc_forms
from apps.greencheck import models as gc_models


logger = logging.getLogger(__name__)


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
