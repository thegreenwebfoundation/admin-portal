
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin, Group
from django.utils.safestring import mark_safe
from django.shortcuts import redirect
from django.template.loader import render_to_string

from apps.greencheck.admin import (
    GreencheckIpApproveInline,
    GreencheckIpInline,
    GreencheckAsnInline,
    GreencheckAsnApproveInline
)

from apps.greencheck.models import GreencheckASN
from apps.greencheck.models import GreencheckIp
from apps.greencheck.models import GreencheckIpApprove
from apps.greencheck.choices import StatusApproval

from .utils import get_admin_name
from .admin_site import greenweb_admin
from . import forms
from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import (
    Datacenter,
    DatacenterCertificate,
    DatacenterClassification,
    DatacenterCooling,
    HostingproviderCertificate,
    Hostingprovider,
    User,
)


@admin.register(Group, site=greenweb_admin)
class CustomGroupAdmin(GroupAdmin):
    pass


@admin.register(User, site=greenweb_admin)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    search_fields = ('username', 'email')
    list_display = [
        'username',
        'email',
        'last_login',
        'is_staff'
    ]

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('email',)}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
    )


class HostingCertificateInline(admin.TabularInline):
    extra = 0
    model = HostingproviderCertificate
    classes = ['collapse']


@admin.register(Hostingprovider, site=greenweb_admin)
class HostingAdmin(admin.ModelAdmin):
    inlines = [
        HostingCertificateInline,
        GreencheckAsnInline,
        GreencheckAsnApproveInline,
        GreencheckIpInline,
        GreencheckIpApproveInline
    ]

    list_display = [
        'name',
        'country_str',
        'html_website',
        'showonwebsite',
        'partner',
        'model',
        'certificates_amount',
        'datacenter_amount',
    ]
    ordering = ('name',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        user = request.user
        user.hostingprovider = obj
        user.save()

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        added = [
            path(
                'approval_asn/',
                self.approve_asn,
                name=get_admin_name(self.model, 'approval_asn')
            ),
            path(
                'approval_ip/',
                self.approve_ip,
                name=get_admin_name(self.model, 'approval_ip')
            ),
            path(
                'send_email/<approval_id>/',
                self.send_email,
                name=get_admin_name(self.model, 'send_email')
            ),
        ]
        # order is important !!
        return added + urls

    def send_email(self, request, *args, **kwargs):
        email_template = request.GET.get('email')
        email_template = f'emails/{email_template}'
        obj = GreencheckIpApprove.objects.get(pk=kwargs['approval_id'])
        message = render_to_string(email_template, context={})
        send_mail(
            'Regarding your new entry on Green web admin',
            message,
            settings.DEFAULT_FROM_EMAIL,
            [u.email for u in obj.hostingprovider.user_set.all()]
        )

        messages.add_message(
            request, messages.INFO,
            'Email sent to user'
        )

        name = 'admin:' + get_admin_name(self.model, 'change')
        return redirect(name, obj.hostingprovider_id)

    def approve_asn(self, request, *args, **kwargs):
        # TODO it would be ideal if this was more re-usable
        from apps.greencheck.models import GreencheckASNapprove
        pk = request.GET.get('approval_id')
        action = request.GET.get('action')

        obj = GreencheckASNapprove.objects.get(pk=pk)
        obj.status = action
        obj.save()

        if action == StatusApproval.approved:
            GreencheckASN.objects.create(
                active=True,
                hostingprovider=obj.hostingprovider,
                asn=obj.asn
            )
        name = 'admin:' + get_admin_name(self.model, 'change')
        return redirect(name, obj.hostingprovider_id)

    def approve_ip(self, request, *args, **kwargs):
        # TODO it would be ideal if this was more re-usable
        pk = request.GET.get('approval_id')
        action = request.GET.get('action')

        obj = GreencheckIpApprove.objects.get(pk=pk)
        obj.status = action
        obj.save()

        if action == StatusApproval.approved:
            GreencheckIp.objects.create(
                active=True,
                hostingprovider=obj.hostingprovider,
                ip_start=obj.ip_start,
                ip_end=obj.ip_end
            )
        name = 'admin:' + get_admin_name(self.model, 'change')
        return redirect(name, obj.hostingprovider_id)

    def save_formset(self, request, form, formset, change):
        """
        We need to let the form know if this an addition or a change
        so that approval record is saved correctly in case of a
        non-staff user.
        """

        # A bit of a hack, we need to let the form know that it has changed
        # somehow, this was the easiest way of doing it.
        formset.form.changed = change
        formset.save()

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_staff:
            return ['partner']
        return self.readonly_fields

    def _changeform_view(self, request, object_id, form_url, extra_context):
        '''Include whether current user is staff, so it can be picked up by a form'''
        if request.method == 'POST':
            post = request.POST.copy()
            post['is_staff'] = request.user.is_staff
            request.POST = post
        return super()._changeform_view(request, object_id, form_url, extra_context)

    def get_fieldsets(self, request, obj=None):
        fieldset = [
            ('Hostingprovider info', {
                'fields': (('name', 'website',), 'country'),
            }),
            ('Visual', {'fields': (('icon', 'iconurl'),)}),
            ('Other', {'fields': (('partner', 'model'),)}),
        ]

        admin_editable = (
            'Admin only', {'fields': (('archived', 'showonwebsite', 'customer'),)}
        )
        if request.user.is_staff:
            fieldset.append(admin_editable)
        return fieldset

    def get_queryset(self, request, *args, **kwargs):
        qs = super().get_queryset(request, *args, **kwargs)
        qs = qs.prefetch_related(
            'hostingprovider_certificates',
            'datacenter'
        )
        if not request.user.is_staff:
            qs = qs.filter(user=request.user)
        return qs

    @mark_safe
    def html_website(self, obj):
        html = f'<a href="{obj.website}" target="_blank">{obj.website}</a>'
        return html
    html_website.short_description = 'website'

    def country_str(self, obj):
        return obj.country.code
    country_str.short_description = 'country'

    def certificates_amount(self, obj):
        return len(obj.hostingprovider_certificates.all())
    certificates_amount.short_description = 'Certificates'

    def datacenter_amount(self, obj):
        return len(obj.datacenter.all())
    datacenter_amount.short_description = 'Datacenters'


class DatacenterCertificateInline(admin.TabularInline):
    extra = 0
    model = DatacenterCertificate
    classes = ['collapse']

    # def get_formset(self, request, obj=None, **kwargs):
    # give kwargs a dictionary of widgets to change widgets.


class DatacenterClassificationInline(admin.TabularInline):
    extra = 0
    model = DatacenterClassification
    classes = ['collapse']


class DatacenterCoolingInline(admin.TabularInline):
    extra = 0
    model = DatacenterCooling
    classes = ['collapse']


@admin.register(Datacenter, site=greenweb_admin)
class DatacenterAdmin(admin.ModelAdmin):
    form = forms.DatacenterAdminForm
    inlines = [
        DatacenterCertificateInline,
        DatacenterClassificationInline,
        DatacenterCoolingInline,
    ]

    list_display = [
        'name',
        'html_website',
        'country_str',
        'model',
        'pue',
        'classification_names',
        'show_website',
        'mja3',
        'certificates_amount',
        'hostingproviders_amount'
    ]
    ordering = ('name',)
    raw_id_fields = ('user',)

    def get_queryset(self, request, *args, **kwargs):
        qs = super().get_queryset(request, *args, **kwargs)
        qs = qs.prefetch_related(
            'classifications',
            'datacenter_certificates',
            'hostingproviders'
        )

        if not request.user.is_staff:
            qs = qs.filter(user=request.user)
        return qs

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_staff:
            return ['showonwebsite']
        return self.readonly_fields

    def get_fieldsets(self, request, obj=None):
        fieldset = [
            ('Datacenter info', {
                'fields': (
                    ('name', 'website',),
                    ('country', 'user'),
                    ('pue', 'residualheat'),
                    ('temperature', 'temperature_type',),
                    ('dc12v', 'virtual', 'greengrid', 'showonwebsite'),
                    ('mja3', 'model',),
                ),

            }),
            (None, {
                'fields': ('hostingproviders',)
            })
        ]
        return fieldset

    @mark_safe
    def html_website(self, obj):
        html = f'<a href="{obj.website}" target="_blank">{obj.website}</a>'
        return html
    html_website.short_description = 'website'

    def country_str(self, obj):
        return obj.country.code
    country_str.short_description = 'country'

    def show_website(self, obj):
        return obj.showonwebsite
    show_website.short_description = 'Show on website'
    show_website.boolean = True

    def classification_names(self, obj):
        classifications = [c.classification for c in obj.classifications.all()]
        return ', '.join(classifications)
    classification_names.short_description = 'Classifications'

    def certificates_amount(self, obj):
        return len(obj.datacenter_certificates.all())
    certificates_amount.short_description = 'Certificates'

    def hostingproviders_amount(self, obj):
        return len(obj.hostingproviders.all())
    hostingproviders_amount.short_description = 'Hosters'

