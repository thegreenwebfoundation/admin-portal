import re
import logging

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.urls import path
from django.urls import reverse
from django.shortcuts import render

from django.views.generic.edit import FormView
from django import forms

import ipwhois

from apps.greencheck.views import GreenUrlsView

from ..greencheck import domain_check
from ..greencheck import models as gc_models

checker = domain_check.GreenDomainChecker()

logger = logging.getLogger(__name__)


class CheckUrlForm(forms.Form):
    """
    A form for checking a url against the database and surfacing
    what other the information we can see from third part services.
    """

    url = forms.URLField()
    green_status = False
    whois_info = None
    check_result = None
    sitecheck = None

    def clean_url(self):
        """
        Check the submitted url against the TGWF green
        domain database.
        """
        # TODO: decided if we should split this into a
        # separate method. clean_field typically doesn't make
        # other requests

        url = self.cleaned_data["url"]

        domain_to_check = checker.validate_domain(url)
        ip_address = checker.convert_domain_to_ip(domain_to_check)
        whois_lookup = ipwhois.IPWhois(ip_address)

        # returns a green domain object, not our sitecheck, which
        # contains the kind of match we used
        # TODO rewrite this. the sitecheck / greendomain thing is
        # clumsy to use
        res = checker.perform_full_lookup(domain_to_check)
        sitecheck = checker.check_domain(domain_to_check)
        rdap = whois_lookup.lookup_rdap(depth=1)

        # import json
        # radp_json_dump = open(f"{domain_to_check}.radp.lookup.json", "w")
        # radp_json_dump.write(json.dumps(rdap))
        # radp_json_dump.close()

        self.whois_info = rdap
        self.domain = domain_to_check
        self.green_status = res.green
        self.check_result = res
        self.sitecheck = sitecheck


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
        return ctx

    def form_valid(self, form):
        green_status = form.green_status
        ctx = self.get_context_data()

        if form.whois_info:
            ctx["domain"] = form.domain
            ctx["ip_lookup"] = form.whois_info["query"]
            ctx["whois_info"] = form.whois_info

        #
        if form.sitecheck.green and form.sitecheck.match_type == "as":
            # this is an AS match. Point to the ASN match
            as_match = gc_models.GreencheckASN.objects.filter(
                id=form.sitecheck.match_ip_range
            )
            if as_match:
                ctx["matching_green_as"] = as_match[0]

        if form.sitecheck.green and form.sitecheck.match_type == "ip":
            ip_match = gc_models.GreencheckIp.objects.filter(
                id=form.sitecheck.match_ip_range
            )
            if ip_match:
                ctx["matching_green_ip"] = ip_match[0]

        ctx["green_status"] = "green" if green_status else "gray"

        return render(self.request, self.template_name, ctx)


class GreenWebAdmin(AdminSite):
    # This is a standard authentication form that allows non-staff users
    login_form = AuthenticationForm
    index_template = "admin_index.html"
    site_header = "The Green Web Foundation Administration Site"
    index_title = "The Green Web Foundation Administration Site"
    login_template = "login.html"
    logout_template = "logout.html"

    def has_permission(self, request):
        """
        Just check that the user is active, we want
        non-staff users to be able to access admin too.
        """
        return request.user.is_active

    def get_urls(self):
        urls = super().get_urls()
        patterns = [
            path("try_out/", CheckUrlView.as_view(), name="check_url"),
            path("green-urls", GreenUrlsView.as_view(), name="green_urls"),
        ]
        return patterns + urls

    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        app_list += [
            {
                "name": "Try out greencheck",
                "app_label": "greencheck",
                "app_url": reverse("admin:check_url"),
                "models": [
                    {
                        "name": "Try out a url",
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
