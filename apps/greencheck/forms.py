import logging

from django import forms
from django.forms import ModelForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .choices import ActionChoice
from .choices import StatusApproval
from .models import GreencheckIp
from .models import GreencheckIpApprove
from .models import GreencheckASN, GreencheckASNapprove

User = get_user_model()

logger = logging.getLogger(__name__)


class ChangeStateRequiredError(Exception):
    """
    An exception to catch the case when the approval mixin us used,
    but the `changed` attribute is not being set by a subclass.
    """

    pass


class ApprovalMixin:
    """
    A mixin to hold the logic for IP and ASN approval forms.

    Contains the logic for our 'admin hack' to make approval requests
    as new or updates
    """

    ApprovalModel = None

    def check_if_changed(self):
        """
        Check if we have a changed attribute, otherwise raise an meaningful
        helpful exception
        """

        # add our sanity check
        if not hasattr(self, "changed"):
            raise ChangeStateRequiredError(
                (
                    "the 'changed' attribute needs to be set on a form for "
                    "approval checking to work properly"
                )
            )

        return self.changed

    def _save_approval(self):
        """
        Save the approval request, be it an IP Range or an AS Network.

        We expect the form to have the attirbute 'changed' before any call to
        save() - usually after passing values in, but before calling is_valid()

        """

        changed = self.check_if_changed()

        if self.ApprovalModel is None:
            raise NotImplementedError("Approval model missing")

        model_name = self.ApprovalModel._meta.model_name
        if not self.cleaned_data["is_staff"]:
            hosting_provider = self.instance.hostingprovider

            # changed here is set in the formset and
            # represents whether we are updating an existing ip range or ASN,
            # or creating a totally new one.
            action = ActionChoice.UPDATE if changed else ActionChoice.NEW
            status = StatusApproval.UPDATE if changed else StatusApproval.NEW
            kwargs = {
                "action": action,
                "status": status,
                "hostingprovider": hosting_provider,
            }

            if model_name == "greencheckasnapprove":
                self.instance = GreencheckASNapprove(asn=self.instance.asn, **kwargs)
            else:
                self.instance = GreencheckIpApprove(
                    ip_end=self.instance.ip_end,
                    ip_start=self.instance.ip_start,
                    **kwargs
                )

            hosting_provider.mark_as_pending_review(self.instance)

    def clean_is_staff(self):
        try:
            # when using this form `is_staff` should always be available
            # or else something has gone wrong...
            return self.data["is_staff"]
        except KeyError:
            raise ValidationError("Alert staff: a bug has occurred.")


class GreencheckAsnForm(ModelForm, ApprovalMixin):
    ApprovalModel = GreencheckASNapprove

    is_staff = forms.BooleanField(
        label="user_is_staff", required=False, widget=forms.HiddenInput()
    )

    class Meta:
        model = GreencheckASN
        fields = (
            "active",
            "asn",
        )

    def save(self, commit=True):
        """
        """
        # Like the GreencheckIpForm, we non-staff user creates an ip, instead of saving
        self._save_approval()
        return super().save(commit=True)


class GreencheckIpForm(ModelForm, ApprovalMixin):
    """
    If a non staff user fills in the form, we return an unsaved
    an unsaved approval record instead of greencheckip record
    """

    ApprovalModel = GreencheckIpApprove
    is_staff = forms.BooleanField(
        label="user_is_staff", required=False, widget=forms.HiddenInput()
    )

    class Meta:
        model = GreencheckIp
        fields = (
            "active",
            "ip_start",
            "ip_end",
        )

    def save(self, commit=True):
        """
        If a non-staff user creates an ip, instead of saving
        the ip record directly, we save an approval record.

        Once the IP range approval request is a approved, we create the
        IP.

        If a staff user saves, we create it directly.
        """
        self._save_approval()
        return super().save(commit=commit)


class GreencheckAsnApprovalForm(ModelForm):
    class Meta:
        model = GreencheckASNapprove
        fields = ("action", "asn", "status")

    def save(self, commit=True):
        instance = self.instance.greencheck_asn
        if commit is True:
            if instance:
                instance.asn = self.instance.asn
                instance.save()
            else:
                instance = GreencheckASN.objects.create(
                    active=True,
                    asn=self.instance.asn,
                    hostingprovider=self.instance.hostingprovider,
                )
        self.instance.greencheck_asn = instance
        return super().save(commit=commit)


class GreecheckIpApprovalForm(ModelForm):

    field_order = ("ip_start", "ip_end")

    class Meta:
        model = GreencheckIpApprove
        fields = "__all__"

    def save(self, commit=True):
        """
        """
        ip_instance = self.instance.greencheck_ip
        if commit is True:
            if ip_instance:
                ip_instance.ip_end = self.instance.ip_end
                ip_instance.ip_end = self.instance.ip_start
                ip_instance.save()
            else:
                ip_instance = GreencheckIp.objects.create(
                    active=True,
                    ip_end=self.instance.ip_end,
                    ip_start=self.instance.ip_start,
                    hostingprovider=self.instance.hostingprovider,
                )
        self.instance.greencheck_ip = ip_instance
        return super().save(commit=commit)
