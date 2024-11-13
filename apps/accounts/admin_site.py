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
from django.views.generic.edit import FormView
from waffle.mixins import WaffleFlagMixin

from apps.greencheck.views import GreenUrlsView

from ..greencheck import carbon_txt, domain_check
from ..greencheck import models as gc_models


checker = domain_check.GreenDomainChecker()
logger = logging.getLogger(__name__)


class CarbonTxtForm(forms.Form):
    """
    A form for previewing what is in the database given a carbon txt file,
    at a specific domain.
    You can also paste the carbon.txt contents into a textfield, for convenience.
    """

    url = forms.URLField()
    body = forms.CharField(widget=forms.Textarea(attrs={"rows": 30}), required=False)

    preview = None
    parser = carbon_txt.CarbonTxtParser()

    def clean(self):
        submitted_text = self.cleaned_data["body"]
        url = self.cleaned_data["url"]
        parsed_toml = None

        # check that the submitted text is valid TOML

        if not submitted_text:
            try:
                response = self.parser.parse_from_url(url)
                self.cleaned_data["preview"] = response

                # return early
                return
            except Exception as ex:
                logger.exception(ex)
                # flag up an error about the domain
                raise forms.ValidationError(
                    "Unable to fetch a valid carbon.txt from url: %(url)s",
                    code="bad_http_lookup",
                    params={"url": url},
                )

        if submitted_text:
            if isinstance(submitted_text, bytes):
                submitted_text = submitted_text.decode("utf-8")
            try:
                parsed_toml = toml.loads(submitted_text)
            except toml.decoder.TomlDecodeError:
                logger.warn(f"Unable to read TOML at {url}")
                raise forms.ValidationError(
                    "Unable to parse the provided TOML.", code="toml_parse_error"
                )

            parsed_url = parse.urlparse(url)
            domain = parsed_url.netloc

            if parsed_toml:
                try:
                    self.cleaned_data["preview"] = self.parser.parse(
                        domain, submitted_text
                    )
                except Exception as ex:
                    logger.warning(f"{ex}")

                    raise forms.ValidationError(
                        f"The carbon.txt file contained valid TOML, but there was a problem performing lookups with the given info.",
                        code="carbon_txt_lookup_error",
                    )


class CarbonTxtCheckView(WaffleFlagMixin, LoginRequiredMixin, FormView):
    template_name = "carbon_txt_preview.html"
    form_class = CarbonTxtForm
    success_url = "/admin/carbon-txt-preview"
    waffle_flag = "carbon_txt_preview"

    def form_valid(self, form):
        """Show the valid"""

        ctx = self.get_context_data()

        preview = form.cleaned_data.get("preview")

        if preview:
            ctx["preview"] = form.cleaned_data["preview"]

        # return early if no submitted text
        return render(self.request, self.template_name, ctx)


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
        domain_to_check = checker.validate_domain(url)

        # check if we can resolve to an IP - this catches when
        # people provide an IP address
        try:
            checker.convert_domain_to_ip(domain_to_check)
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
    site_header = "The Green Web Foundation Administration Site"
    index_title = "The Green Web Foundation Administration Site"
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
