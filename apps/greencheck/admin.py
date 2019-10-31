from django.contrib import admin

from .models import (
    GreencheckIp,
    GreencheckIpApprove,
)


@admin.register(GreencheckIp)
class GreencheckIpAdmin(admin.ModelAdmin):
    pass


@admin.register(GreencheckIpApprove)
class GreencheckIpApprove(admin.ModelAdmin):
    pass


