from django import forms
from django.forms import ModelForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .choices import ActionChoice
from .choices import StatusApproval
from .models import GreencheckIp
from .models import GreencheckIpApprove


User = get_user_model()


class GreencheckIpForm(ModelForm):
    '''This form is meant for admin

    If a non staff user fills in the form it would return
    an unsaved approval record instead of greencheckip record
    '''

    is_staff = forms.BooleanField(
        label='user_is_staff', required=False, widget=forms.HiddenInput()
    )

    class Meta:
        model = GreencheckIp
        fields = '__all__'

    def clean_is_staff(self):
        try:
            # when using this form `is_staff` should always be available
            # or else something has gone wrong...
            return self.data['is_staff']
        except KeyError:
            raise ValidationError('Alert staff: a bug has occurred.')

    def save(self, commit=True):
        '''
        If a non-staff user creates an ip, instead of saving
        the ip record directly, it will save an approval record.

        Only when it has been approved the record will actually
        be created.

        So we return an approval instance instead of Greencheck instance
        which in turn will get saved a bit later.
        '''
        if not self.cleaned_data['is_staff']:
            # change the instance.
            # i need to know if this is a change request.
            action = ActionChoice.update if self.changed else ActionChoice.new
            status = StatusApproval.update if self.changed else StatusApproval.new
            self.instance = GreencheckIpApprove(
                action=action,
                hostingprovider=self.instance.hostingprovider,
                ip_end=self.instance.ip_end,
                ip_start=self.instance.ip_start,
                status=status
            )
        # check initial data for the request user.
        return super().save(commit=commit)
