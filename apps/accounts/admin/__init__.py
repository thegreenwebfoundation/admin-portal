from django.contrib import admin
from rest_framework_api_key.admin import APIKeyModelAdmin as BaseAPIKeyModelAdmin

from waffle.admin import FlagAdmin
from waffle.models import Flag


from ..admin_site import greenweb_admin
from ..models import APIKey, APIKeyPrivilegeLevel, APIService

from .user import CustomGroupAdmin, CustomUserAdmin
from .hosting.provider import (
    ServiceAdmin,
    VerificationBasisAdmin,
    LabelAdmin,
    SupportMessageAdmin,
    HostingAdmin
)
from .hosting.datacenter import DatacenterNoteInline, DatacenterAdmin
from .hosting.carbon_txt import CarbonTxtMotivationAdmin, ProviderCarbonTxtAdmin
from .provider_request import ProviderRequest
from .log_entry import GWLogEntryAdmin


class APIKeyPrivilegeLevelAdmin(admin.ModelAdmin):
    model=APIKeyPrivilegeLevel
    list_display=["name"]

class APIServiceAdmin(admin.ModelAdmin):
    model=APIService
    list_display=["name", "key"]

class APIKeyModelAdmin(BaseAPIKeyModelAdmin):
    list_display = ["user"] + [f for f in BaseAPIKeyModelAdmin.list_display if f != "name"]
    readonly_fields = [f for f in BaseAPIKeyModelAdmin.readonly_fields if f != "name"]

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if "name" in fields:
            fields.remove("name")
        if "note" not in fields:
            fields.append("note")
        if "privilege_level" not in fields:
            fields.append("privilege_level")
        if "service" not in fields:
            fields.append("service")
        if "motivation" not in fields:
            fields.append("motivation")
        return fields

greenweb_admin.register(APIKey, APIKeyModelAdmin)
greenweb_admin.register(APIKeyPrivilegeLevel, APIKeyPrivilegeLevelAdmin)
greenweb_admin.register(APIService, APIServiceAdmin)
greenweb_admin.register(Flag, FlagAdmin)

