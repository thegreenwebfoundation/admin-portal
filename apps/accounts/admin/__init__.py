
from waffle.admin import FlagAdmin
from waffle.models import Flag


from ..admin_site import greenweb_admin

from .user import CustomGroupAdmin, CustomUserAdmin
from .hosting.provider import (
    ServiceAdmin,
    VerificationBasisAdmin,
    LabelAdmin,
    LinkedDomainAdmin,
    SupportMessageAdmin,
    HostingAdmin
)
from .hosting.datacenter import DatacenterNoteInline, DatacenterAdmin
from .provider_request import ProviderRequest
from .log_entry import GWLogEntryAdmin




greenweb_admin.register(Flag, FlagAdmin)

