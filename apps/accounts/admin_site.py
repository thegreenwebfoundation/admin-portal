import json
import re
import socket
from urllib.parse import urlparse

import requests
from django import forms
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.shortcuts import render
from django.urls import path, reverse
from django.views.generic.edit import FormView
from ipwhois import IPWhois
from requests.exceptions import HTTPError

from apps.greencheck.views import GreenUrlsView

URL_RE = re.compile(r"https?:\/\/(.*)")
BASE_URL = "https://api.thegreenwebfoundation.org/greencheck"


class CheckUrlForm(forms.Form):
    url = forms.URLField()

    def clean_url(self):
        url = self.cleaned_data["url"]
        url_check = URLValidator()
        # if this is valid, nothing should be raised
        url_check(url)
        return url


class CheckUrlView(FormView):
    template_name = "try_out.html"
    form_class = CheckUrlForm
    success_url = "/not/used"

    def greencheck(self, domain):
        resp = requests.get(f"{BASE_URL}/{domain}")
        resp.raise_for_status()
        return resp.json()

    def whois_check(self, domain):
        ip_address = socket.gethostbyname(domain)
        obj = IPWhois(ip_address)
        return obj.lookup_rdap(depth=1)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_url"] = reverse("admin:check_url")
        return context

    def form_valid(self, form):
        url = form.data.get("url")
        domain = urlparse(url).netloc

        greencheck = self.greencheck(domain)
        whois_check = self.whois_check(domain)
        green = greencheck.get("green")
        context = self.get_context_data()

        context["green_status"] = "green" if green else "gray"
        context["whois_check"] = whois_check
        context["greencheck"] = greencheck

        return render(self.request, self.template_name, context)


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
