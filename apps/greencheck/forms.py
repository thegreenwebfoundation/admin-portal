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


class ApprovalMixin:
    ApprovalModel = None

    def _save_approval(self):
        """
        Save the approval request, be it an IP Range or an AS Network
        from a
        """
        if self.ApprovalModel is None:
            raise NotImplementedError("Approval model missing")

        model_name = self.ApprovalModel._meta.model_name
        if not self.cleaned_data["is_staff"]:
            hosting_provider = self.instance.hostingprovider

            # changed here represents an
            action = ActionChoice.UPDATE if self.changed else ActionChoice.NEW
            status = StatusApproval.UPDATE if self.changed else StatusApproval.NEW
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
        self._save_approval()
        return super().save(commit=True)


class GreencheckIpForm(ModelForm, ApprovalMixin):
    """This form is meant for admin

    If a non staff user fills in the form it would return
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
        the ip record directly, it will save an approval record.

        Only when it has been approved the record will actually
        be created.

        So we return an approval instance instead of Greencheck instance
        which in turn will get saved a bit later.
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
