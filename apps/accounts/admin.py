from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe

from apps.greencheck.admin import (
    GreencheckIpApproveInline,
    GreencheckIpInline,
)

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import (
    Datacenter,
    HostingproviderCertificate,
    Hostingprovider,
    User,
)


@admin.register(User)
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


@admin.register(Hostingprovider)
class HostingAdmin(admin.ModelAdmin):
    inlines = [
        HostingCertificateInline,
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


@admin.register(Datacenter)
class DatacenterAdmin(admin.ModelAdmin):
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

    def get_queryset(self, request, *args, **kwargs):
        qs = super().get_queryset(request, *args, **kwargs)
        qs = qs.prefetch_related(
            'classifications',
            'datacenter_certificates',
            'hostingproviders'
        )
        return qs

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

