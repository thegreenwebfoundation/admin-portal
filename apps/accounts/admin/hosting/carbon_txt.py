from django.contrib import admin

from ...admin_site import greenweb_admin
from ...models import (
    CarbonTxtMotivation,
    ProviderCarbonTxtMotivation,
    ProviderCarbonTxt
)

@admin.register(CarbonTxtMotivation, site=greenweb_admin)
class CarbonTxtMotivationAdmin(admin.ModelAdmin):
    model = CarbonTxtMotivation

    class Meta:
        verbose_name = "Motivations for using carbon.txt"

@admin.register(ProviderCarbonTxtMotivation, site=greenweb_admin)
class ProviderCarbonTxtMotivationAdmin(admin.ModelAdmin):
    model = ProviderCarbonTxtMotivation

    list_display = ["content_object", "tag", "description"]
    list_select_related = ["content_object", "tag"]

    class Meta:
        verbose_name = "Provider's motivations for using carbon.txt"

@admin.register(ProviderCarbonTxt, site=greenweb_admin)
class ProviderCarbonTxtAdmin(admin.ModelAdmin):
    model = ProviderCarbonTxt

    list_display = ["provider", "domain", "state"]
    list_select_related = ["provider"]

    class Meta:
        verbose_name = "provider carbon.txts"
