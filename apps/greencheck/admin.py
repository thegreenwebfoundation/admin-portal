from django.contrib import admin

from .models import (
    GreencheckIp,
    GreencheckIpApprove,
)
from .forms import GreencheckIpForm
from .forms import GreecheckIpApprovalForm


class GreencheckIpInline(admin.TabularInline):
    extra = 0
    model = GreencheckIp
    classes = ['collapse']
    form = GreencheckIpForm
    ordering = ('ip_start', 'ip_end',)


class GreencheckIpApproveInline(admin.TabularInline):
    extra = 0
    form = GreecheckIpApprovalForm
    model = GreencheckIpApprove
    ordering = ('ip_start', 'ip_end',)
    # filter away records that are already approved.


