from django.utils.safestring import mark_safe
from django.contrib import admin

from apps.accounts.utils import reverse_admin_name
from apps.accounts.models import Hostingprovider
from .models import (
    GreencheckIp,
    GreencheckIpApprove,
)
from . import forms
from . import models
from .forms import GreencheckIpForm
from .forms import GreecheckIpApprovalForm
from .choices import StatusApproval


class ApprovalFieldMixin:

    @mark_safe
    def approval(self, obj):
        if obj._meta.model_name == 'greencheckasnapprove':
            name = 'approval_asn'
        else:
            name = 'approval_ip'

        approve_url = reverse_admin_name(
            Hostingprovider,
            name=name,
            params={
                'action': StatusApproval.approved,
                'approval_id': obj.pk
            }
        )
        reject_url = reverse_admin_name(
            Hostingprovider,
            name=name,
            params={
                'action': StatusApproval.removed,
                'approval_id': obj.pk
            }
        )

        approve = f'<a href="{approve_url}">Approve</a>'
        reject = f'<a href="{reject_url}">Reject</a>'
        link = f'{approve} / {reject}'
        action_taken = any([
            obj.status == StatusApproval.deleted,
            obj.status == StatusApproval.removed,
            obj.status == StatusApproval.approved
        ])
        if action_taken:
            return 'Action taken'
        return link
    approval.short_description = 'Decide'


class GreencheckAsnInline(admin.TabularInline):
    extra = 0
    form = forms.GreencheckAsnForm
    model = models.GreencheckASN
    ordering = ('asn',)
    verbose_name = 'ASN'
    verbose_name_plural = 'ASN'


class GreencheckAsnApproveInline(admin.TabularInline, ApprovalFieldMixin):
    classes = ['collapse']
    extra = 0
    form = forms.GreencheckAsnApprovalForm
    model = models.GreencheckASNapprove
    ordering = ('asn',)
    verbose_name = 'ASN approval'
    verbose_name_plural = 'ASN approvals'

    readonly_fields = ('action', 'status', 'approval', 'created')

    def get_fieldsets(self, request, obj=None):
        fields = (
            'created',
            'asn',
            'action',
            'status',
        )

        if request.user.is_staff:
            fields = fields + ('approval',)

        fieldsets = (
            (None, {'fields': fields}),
        )
        return fieldsets

    def get_readonly_fields(self, request, obj):
        '''Non staff user should only be able to read the fields'''
        read_only = super().get_readonly_fields(request, obj)
        if not request.user.is_staff:
            read_only = ('asn',) + read_only
        return read_only


class GreencheckIpInline(admin.TabularInline):
    extra = 0
    form = GreencheckIpForm
    model = GreencheckIp
    ordering = ('ip_start', 'ip_end',)
    verbose_name = 'IP'
    verbose_name_plural = 'IPs'


class GreencheckIpApproveInline(admin.TabularInline, ApprovalFieldMixin):
    classes = ['collapse']
    extra = 0
    form = GreecheckIpApprovalForm
    model = GreencheckIpApprove
    ordering = ('ip_start', 'ip_end',)
    verbose_name = 'IP approval'
    verbose_name_plural = 'IP approvals'

    readonly_fields = ('action', 'status', 'approval', 'created')

    class Media:
        js = (
            'admin/js/vendor/jquery/jquery.js',
            'admin/js/jquery.init.js',
            'greencheck/js/email.js',
        )

    def get_fieldsets(self, request, obj=None):
        fields = (
            'created',
            'ip_start',
            'ip_end',
            'action',
            'status',
        )

        if request.user.is_staff:
            fields = fields + (
                'approval',
            )

        fieldsets = (
            (None, {'fields': fields}),
        )
        return fieldsets

    def get_readonly_fields(self, request, obj):
        '''Non staff user should only be able to read the fields'''
        read_only = super().get_readonly_fields(request, obj)
        if not request.user.is_staff:
            read_only = ('ip_start', 'ip_end') + read_only
        return read_only
