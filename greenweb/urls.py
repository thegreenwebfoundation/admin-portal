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
from django.urls import path, include
from django.http import HttpResponse
from rest_framework.routers import DefaultRouter
from apps.greencheck.viewsets import IPRangeViewSet

from apps.accounts.admin_site import greenweb_admin as admin
from apps.accounts import urls as accounts_urls

urlpatterns = []

router = DefaultRouter()
router.register(r"ip-ranges", IPRangeViewSet, basename="ip-range")


if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]

urlpatterns += [
    path("", admin.urls),
    path("", include(accounts_urls)),
    path("api/v2/", include(router.urls)),
]
