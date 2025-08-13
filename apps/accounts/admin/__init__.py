
from waffle.admin import FlagAdmin
from waffle.models import Flag


from ..admin_site import greenweb_admin

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




greenweb_admin.register(Flag, FlagAdmin)

