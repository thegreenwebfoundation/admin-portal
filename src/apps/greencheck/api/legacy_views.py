import logging


from django.views.decorators.cache import cache_page
from django_countries import countries
from rest_framework import response
from rest_framework import exceptions
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import AllowAny
from rest_framework_jsonp.renderers import JSONPRenderer

from ...accounts.models import Hostingprovider
from ..domain_check import GreenDomainChecker

logger = logging.getLogger(__name__)

checker = GreenDomainChecker()

def fetch_providers_for_country(country_code):
    """
    Return all the country providers that should be visible
    as a list, with partners listed first, then in
    alphabetical order.
    """
    # we need to order by partner, then alphabetical
    # order. Because the django ORM doesn't natively support
    # group by, and because we have hundreds of hosters for each
    # country, at a maximum we can get away with doing it in memory

    all_providers = Hostingprovider.objects.filter(
        country=country_code, is_listed=True
    )

    # because historically we have had a mix of empty strings and null
    # values, we need to use multiple excludes
    partner_providers = (
        all_providers.filter(country=country_code, is_listed=True)
        .filter(partner__isnull=False)
        .exclude(partner__in=["", "None"])
        .order_by("name")
    )

    regular_providers = all_providers.exclude(id__in=partner_providers).order_by("name")

    # destructure the providers to build a new list,
    # with partner providers first, then regular providers
    providers = [*partner_providers, *regular_providers]

    return [
        {
            "iso": str(provider.country),
            "id": str(provider.id),
            "naam": provider.name,
            "website": provider.website,
            "partner": provider.partner,
        }
        for provider in providers
    ]


@api_view()
@permission_classes([AllowAny])
@renderer_classes([JSONPRenderer])
@cache_page(60 * 15)
def directory(request):
    """
    Return a JSON object keyed by countrycode, listing the providers
    we have for each country:
    """
    country_list = {}

    for country in countries:
        country_obj = {
            "iso": country.code,
            "tld": f".{country.code.lower()}",
            "countryname": country.name.upper(),
        }

        providers = fetch_providers_for_country(country.code)
        if providers:
            country_obj["providers"] = providers

        country_list[country.code] = country_obj

    return response.Response(country_list)


@api_view()
@permission_classes([AllowAny])
def directory_provider(self, id):
    """
    Return a JSON object representing the provider,
    what they do, and evidence supporting their
    sustainability claims
    """
    try:
        provider_id = int(id)
    except ValueError as ex:
        logger.warning(ex)
        raise exceptions.ParseError(
            (
                "You need to send a valid numeric ID to identify the "
                "provider you are requesting information about. "
                f"Received ID was: '{id}'"
            )
        )

    provider = Hostingprovider.objects.get(pk=provider_id)
    datacenters = [dc.legacy_representation() for dc in provider.datacenter.all() if dc]

    from urllib import parse

    # we strip out the protocol from our links because when the directory code is
    # consumed in some old jquery code running in the browser to render our directory
    # hyperlinks are mangled, and http://my-domain ends up as http//mydomain
    # for more, see the trello card below
    # https://trello.com/c/8Ou3mATw/124
    domain_with_no_protocol = parse.urlparse(provider.website).netloc

    # basic case, no datacenters or certificates
    provider_dict = {
        "id": str(provider.id),
        "naam": provider.name,
        # "website": provider.website,
        "website": domain_with_no_protocol,
        "countrydomain": str(provider.country),
        "model": provider.model,
        "certurl": None,
        "valid_from": None,
        "valid_to": None,
        "mainenergytype": None,
        "energyprovider": None,
        "partner": provider.partner,
        "datacenters": datacenters,
    }
    return response.Response([provider_dict])


