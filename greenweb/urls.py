"""Greenweb foundation URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/dev/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.urls import path, include, reverse_lazy
from django.views.generic.base import RedirectView
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter


from apps.greencheck.viewsets import (
    IPRangeViewSet,
    ASNViewSet,
    GreenDomainViewset,
    GreenDomainBatchView,
)

from apps.greencheck.swagger import TGWFSwaggerView

from apps.greencheck.api import legacy_views
from apps.greencheck.api import image_views
from apps.greencheck.api import views as api_views
from apps.accounts.admin import LabelAutocompleteView
from apps.accounts import urls as accounts_urls
from rest_framework.authtoken import views

from apps.greencheck import urls as greencheck_urls, directory_urls
from apps.theme.views import style_guide

urlpatterns = []

router = DefaultRouter()
router.register(r"ip-ranges", IPRangeViewSet, basename="ip-range")
router.register(r"asns", ASNViewSet, basename="asn")

if settings.DEBUG:
    import importlib
    import debug_toolbar

    # enable debug toolbar
    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]

    # only try adding the reload urls if we have the module installed
    if importlib.util.find_spec("django_browser_reload"):
        urlpatterns += [
            path("__reload__/", include("django_browser_reload.urls")),
        ]

    # serve uploaded files locally
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


urlpatterns += [
    path("", include(accounts_urls)),
    path(
        "green-urls",
        RedirectView.as_view(url=reverse_lazy("greenweb_admin:green_urls")),
        name="green_urls_redirect",
    ),
    path(
        "label-autocomplete",
        LabelAutocompleteView.as_view(),
        name="label-autocomplete",
    ),
    # API
    path("api/v3/", include(router.urls)),
    path(
        "api/v3/greencheck/",
        GreenDomainViewset.as_view({"get": "list"}),
        name="green-domain-list",
    ),
    path(
        "api/v3/greencheck/<url>",
        GreenDomainViewset.as_view({"get": "retrieve"}),
        name="green-domain-detail",
    ),
    path(
        "api/v3/batch/greencheck",
        GreenDomainBatchView.as_view(),
        name="green-domain-batch",
    ),
    path(
        "api/v3/ip-to-co2intensity/",
        api_views.IPCO2Intensity.as_view(),
        name="ip-to-co2intensity",
    ),
    path(
        "api/v3/ip-to-co2intensity/<ip_to_check>",
        api_views.IPCO2Intensity.as_view(),
        name="ip-to-co2intensity",
    ),
    path(
        "api/v3/carbontxt",
        api_views.CarbonTxtAPI.as_view(),
        name="carbon-txt-parse",
    ),
    path(
        "api/v3/carbontxt_shared_secret",
        api_views.ProviderSharedSecretView.as_view(),
        name="carbon-txt-shared-secret",
    ),
    path(
        "api/v3/domain_hash/",
        api_views.DomainHashView.as_view(),
        name="carbon-txt-domain-hash",
    ),
    path(
        "api/v3/domain_claim/",
        api_views.DomainClaimView.as_view(),
        name="carbon-txt-domain-claim",
    ),
    path(
        "api/v3/greencheckimage/<url>",
        image_views.greencheck_image,
        name="greencheck-image",
    ),
    path("api-token-auth/", views.obtain_auth_token, name="api-obtain-token"),
    path(
        "api-docs/",
        TGWFSwaggerView.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    # replicate the PHP API, at the same url, so we can also put
    # it behind the reverse proxy
    path(
        "greencheck/<url>",
        GreenDomainViewset.as_view({"get": "retrieve"}),
        name="green-domain-detail",
    ),
    path(
        "checks/latest/",
        legacy_views.latest_greenchecks,
        name="legacy-latest-greenchecks",
    ),
    path(
        "data/directory/",
        legacy_views.directory,
        name="legacy-directory-listing",
    ),
    path(
        "data/hostingprovider/<id>",
        legacy_views.directory_provider,
        name="legacy-directory-detail",
    ),
    path(
        "greencheckimage/<url>",
        legacy_views.legacy_greencheck_image,
        name="legacy-greencheck-image",
    ),
    path(
        "v2/greencheckmulti/<url_list>",
        legacy_views.greencheck_multi,
        name="legacy-greencheck-multi",
    ),
    path("stats/", include(greencheck_urls)),
    path("directory/", include(directory_urls)),
    path("explorer/", include("explorer.urls")),
    # style guide for front end
    path("style-guide", style_guide, name="style-guide"),
]
