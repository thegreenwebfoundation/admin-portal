"""
This module contains the code needed to adapt swagger to:

1. include the green web foundation branding and navigation
2. remove the unneeded TopBar component
3. Expose the necessary class based views for use in our url conf
"""

from django.conf import settings

from rest_framework import permissions
from drf_yasg.views import get_schema_view, SPEC_RENDERERS
from drf_yasg.renderers import SwaggerUIRenderer
from drf_yasg import openapi

_spec_renderers = tuple(renderer.with_validators([]) for renderer in SPEC_RENDERERS)


schema_view = get_schema_view(
    openapi.Info(
        title="Welcome to the Green Web Foundation Partner API ",
        description=(
            "Use this API to update information about the digital "
            "infrastructure you are using, services you provide to "
            "others, and see the status of providers in your own supply chain."
        ),
        default_version="v3",
        terms_of_service="https://www.thegreenwebfoundation.org/privacy-statement/",
        contact=openapi.Contact(email="support@thegreenwebfoundation.org"),
        license=openapi.License(name="License: Apache 2.0. "),
        x_logo={
            "url": "https://www.thegreenwebfoundation.org/wp-content/themes/tgwf2015/img/top-logo-greenweb.png",  # noqa
            "background": "#000000",
        },
    ),
    url=settings.API_URL,
    public=False,
    permission_classes=(permissions.AllowAny,),
)


class TGWFSwaggerUIRenderer(SwaggerUIRenderer):
    """
    A subclass of the normal Swagger UI Renderer, to allow us to override parts of
    the default template, so we can change logos, and remove unused elements.
    """

    template = "swagger-ui.html"


# then I need to get the method in


class TGWFSwaggerView(schema_view):
    """
    An subclass of the SchemaView in drf-yasg, where pass in our
    modified TGWFSwaggerUIRenderer to the with_ui method that
    generates the interactive Swagger UI.
    """

    @classmethod
    def with_ui(cls, renderer="swagger", cache_timeout=0, cache_kwargs=None):
        renderer_classes = (TGWFSwaggerUIRenderer,) + _spec_renderers
        return cls.as_cached_view(
            cache_timeout, cache_kwargs, renderer_classes=renderer_classes
        )
