from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import User, Hostingprovider, Datacenter


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


@admin.register(Hostingprovider)
class HostingAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'country_str',
        'website',
        'showonwebsite',
        'partner',
        'model',
        # 'certificates', needs another table
        # datacenters, needs another table

    ]
    ordering = ('name',)

    def country_str(self, obj):
        return obj.country.code
    country_str.short_description = 'country'


@admin.register(Datacenter)
class DatacenterAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'website',
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


