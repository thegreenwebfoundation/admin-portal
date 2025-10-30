import logging
import typing
from urllib import parse

import requests
import toml
from django import forms
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.urls import path, reverse
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from waffle.mixins import WaffleFlagMixin

from apps.greencheck.views import GreenUrlsView

from ..greencheck import domain_check
from ..greencheck import models as gc_models
from ..greencheck.network_utils import validate_domain, convert_domain_to_ip

checker = domain_check.GreenDomainChecker()
logger = logging.getLogger(__name__)

class CarbonTxtCheckView(WaffleFlagMixin, LoginRequiredMixin, TemplateView):
    """
    Displays a deprecation notice with a link to the new carbon.txt validator
    on the carbon.txt site itself.
    """
    template_name = "carbon_txt_preview.html"
    waffle_flag = "carbon_txt_preview"

class CheckUrlForm(forms.Form):
    """
    A form for checking a url against the database and surfacing
    what other the information we can see from third part services.
    """

    url = forms.URLField()

    def clean_url(self) -> typing.Union[gc_models.GreenDomain, gc_models.SiteCheck]:
        """
        Check the submitted url against the TGWF green
        domain database.
        """
        url = self.cleaned_data["url"]
        domain_to_check = validate_domain(url)

        # check if we can resolve to an IP - this catches when
        # people provide an IP address
        try:
            convert_domain_to_ip(domain_to_check)
        except Exception as err:
            logger.warning(err)
            raise ValidationError(
                (
                    f"Provided url {url} does not appear have a "
                    f"valid domain: {domain_to_check}. "
                    "Please check and try again."
                )
            )

        return domain_to_check


class CheckUrlView(FormView):
    template_name = "try_out.html"
    form_class = CheckUrlForm
    success_url = "/not/used"

    def lookup_asn(self, domain: str) -> dict:
        """Look up the corresponding ASN for this domain"""
        pass

    def lookup_whois(self, domain: str) -> dict:
        """Lookup the structured"""
        pass

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_url"] = reverse("admin:check_url")

        form_class = self.get_form_class()
        form = form_class(self.request.GET)

        if form.is_valid():
            domain_name = form.cleaned_data["url"]
            lookup_result = checker.extended_domain_info_lookup(domain_name)

            site_check = lookup_result["site_check"]
            green_domain = lookup_result["green_domain"]
            green_status = green_domain.green

            ctx["form"] = form
            ctx["domain"] = domain_name
            ctx["whois_info"] = lookup_result["whois_info"]
            ctx["ip_lookup"] = lookup_result["whois_info"]["query"]
            ctx["carbon_txt"] = green_domain.added_via_carbontxt
            ctx["provider"] = green_domain.hosting_provider

            if site_check.green and site_check.match_type == "as":
                # this is an AS match. Point to the ASN match
                as_match = gc_models.GreencheckASN.objects.filter(
                    id=site_check.match_ip_range
                )
                if as_match:
                    ctx["matching_green_as"] = as_match[0]

            if site_check.green and site_check.match_type == "ip":
                ip_match = gc_models.GreencheckIp.objects.filter(
                    id=site_check.match_ip_range
                )
                if ip_match:
                    ctx["matching_green_ip"] = ip_match[0]

            ctx["green_status"] = "green" if green_status else "gray"

        return ctx

    def get(self, request, *args, **kwargs):
        """Handle GET requests: instantiate a blank version of the form."""

        ctx = self.get_context_data()

        return self.render_to_response(ctx)


class GreenWebAdmin(AdminSite):
    # This is a standard authentication form that allows non-staff users
    login_form = AuthenticationForm
    index_template = "admin_index.html"
    site_header = "Green Web Foundation Administration Site"
    index_title = "Green Web Foundation Administration Site"
    login_template = "auth/login.html"
    logout_template = "auth/logout.html"

    def has_permission(self, request):
        """
        Just check that the user is active, we want
        non-staff users to be able to access admin too.
        """
        return request.user.is_active

    def get_urls(self):
        urls = super().get_urls()
        patterns = [
            path("extended-greencheck/", CheckUrlView.as_view(), name="check_url"),
            path("green-urls", GreenUrlsView.as_view(), name="green_urls"),
            path("import-ip-ranges", GreenUrlsView.as_view(), name="import_ip_ranges"),
            path(
                "carbon-txt-preview",
                CarbonTxtCheckView.as_view(),
                name="carbon_txt_preview",
            ),
        ]
        return patterns + urls

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)

        if app_label:
            return app_list

        verification_request_item = {
            "name": "New provider portal",
            "app_label": "greencheck",
            "app_url": reverse("provider_portal_home"),
            "models": [
                {
                    "name": "Move to a new version of provider portal",
                    "object_name": "greencheck_url",
                    "admin_url": reverse("provider_portal_home"),
                    "view_only": True,
                }
            ],
        }
        app_list.insert(0, verification_request_item)


        # Display carbon.txt related apps in their own sublist, in order not to clutter the main accounts list!
        accounts_app = next(app for app in app_list if app["app_label"] == "accounts")

        provider_carbon_txt = next(
                (model for model in accounts_app["models"] if model["object_name"] == "ProviderCarbonTxt"),
                None
        )
        provider_carbon_txt_motivation = next(
                (model for model in accounts_app["models"] if model["object_name"] == "ProviderCarbonTxtMotivation"),
                None
        )
        carbon_txt_motivation = next(
                (model for model in accounts_app["models"] if model["object_name"] == "CarbonTxtMotivation"),
                None
        )

        carbon_txt_models = []

        if provider_carbon_txt:
            accounts_app["models"].remove(provider_carbon_txt)
            carbon_txt_models.append(provider_carbon_txt)

        if provider_carbon_txt_motivation:
            accounts_app["models"].remove(provider_carbon_txt_motivation)
            carbon_txt_models.append(provider_carbon_txt_motivation)

        if carbon_txt_motivation:
            accounts_app["models"].remove(carbon_txt_motivation)
            carbon_txt_models.append(carbon_txt_motivation)

        app_list.insert(2, {
                "name": "Carbon.txt",
                "app_label": "carbontxt",
                "models": carbon_txt_models,
            },
        )

        app_list += [
            {
                "name": "Try out greencheck",
                "app_label": "greencheck",
                "app_url": reverse("admin:check_url"),
                "models": [
                    {
                        "name": "Perform a extended greencheck",
                        "object_name": "greencheck_url",
                        "admin_url": reverse("admin:check_url"),
                        "view_only": True,
                    }
                ],
            },
            {
                "name": "Download data dump",
                "app_label": "greencheck",
                "app_url": reverse("admin:check_url"),
                "models": [
                    {
                        "name": "Download data dump",
                        "object_name": "greencheck_url",
                        "admin_url": reverse("admin:green_urls"),
                        "view_only": True,
                    }
                ],
            },
        ]
        return app_list


greenweb_admin = GreenWebAdmin(name="greenweb_admin")
from drf_api_logger.models import APILogsModel
from drf_api_logger.admin import APILogsAdmin

greenweb_admin.register(APILogsModel, APILogsAdmin)
