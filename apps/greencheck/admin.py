from django.contrib import admin

from .models import (
    GreencheckIp,
    GreencheckIpApprove,
)
from .forms import GreencheckIpForm
from .forms import GreecheckIpApprovalForm


class GreencheckIpInline(admin.TabularInline):
    classes = ['collapse']
    extra = 0
    form = GreencheckIpForm
    model = GreencheckIp
    ordering = ('ip_start', 'ip_end',)
    verbose_name = 'IP'
    verbose_name_plural = 'IPs'


class GreencheckIpApproveInline(admin.TabularInline):
    extra = 0
    form = GreecheckIpApprovalForm
    model = GreencheckIpApprove
    ordering = ('ip_start', 'ip_end',)
    verbose_name = 'IP approval'
    verbose_name_plural = 'IP approvals'
    # filter away records that are already approved.

    readonly_fields = ('action', 'status')

    def get_readonly_fields(self, request, obj):
        '''Non staff user should only be able to read the fields'''
        read_only = super().get_readonly_fields(request, obj)
        if not request.user.is_staff:
            read_only = ('ip_start', 'ip_end') + read_only
        return read_only
