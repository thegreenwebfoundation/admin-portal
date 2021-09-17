import re

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.urls import path
from django.urls import reverse
from django.shortcuts import render

from django.views.generic.edit import FormView
from django import forms

from apps.greencheck.views import GreenUrlsView
from ..greencheck import domain_check

checker = domain_check.GreenDomainChecker()


class CheckUrlForm(forms.Form):
    """
    A form for checking a url against the database and surfacing
    what other the information we can see from third part services.
    """

    url = forms.URLField()
    green_status = False

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
        res = checker.perform_full_lookup(domain_to_check)

        self.green_status = res.green


class CheckUrlView(FormView):
    template_name = "try_out.html"
    form_class = CheckUrlForm
    success_url = "/not/used"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_url"] = reverse("admin:check_url")
        return context

    def form_valid(self, form):
        green_status = form.green_status
        context = self.get_context_data()
        context["green_status"] = "green" if green_status else "gray"
        return render(self.request, self.template_name, context)


class CarbonTxtCheckForm(forms.Form):
    """
    A form to fetch a carbon.txt file at the provided URL, parse it,
    and show what changes would be made if imported.
    """

    url = forms.URLField()


class CarbonTxtCheckView(FormView):
    template_name = "accounts/preview_carbon_txt.html"
    form_class = CarbonTxtCheckForm
    success_url = "/not/used"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_url"] = reverse("admin:preview_carbon_txt")
        return context

    def form_valid(self, form):
        context = self.get_context_data()
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
            path(
                "preview-carbon-txt",
                CarbonTxtCheckView.as_view(),
                name="preview_carbon_txt",
            ),
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
                "name": "Preview a carbon.txt file",
                "app_label": "greencheck",
                "app_url": reverse("admin:preview_carbon_txt"),
                "models": [
                    {
                        "name": "Preview a carbontxt file",
                        "object_name": "greencheck_url",
                        "admin_url": reverse("admin:preview_carbon_txt"),
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
