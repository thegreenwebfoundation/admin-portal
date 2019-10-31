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
        'show_website',
        'mja3',
        # classifications needs other table
        # certificates needs other table
        # hosters needs other table

    ]

    def country_str(self, obj):
        return obj.country.code
    country_str.short_description = 'country'

    def show_website(self, obj):
        return obj.showonwebsite
    show_website.short_description = 'Show on website'
    show_website.boolean = True

