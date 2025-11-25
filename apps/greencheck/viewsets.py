import csv
import json
import logging
from io import TextIOWrapper

import tld
from rest_framework import pagination, parsers, request, response, viewsets
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema  # noqa

# flake8 doesn't like rest_framework_csv. It's not clear why
from rest_framework_csv import renderers as drf_csv_rndr  # noqa

from .api.ip_range_viewset import IPRangeViewSet  # noqa
from .api.asn_viewset import ASNViewSet  # noqa

from . import models as gc_models
from ..accounts.models import CarbonTxtDomainResultCache
from . import serializers as gc_serializers


logger = logging.getLogger(__name__)


class GreenDomainViewset(viewsets.ReadOnlyModelViewSet):
    """
    The greencheck service to replicate the older PHP API for checking domains.

    Supports the same single and batch API.

    By default serves a response
    from the GreenDomains table, rather than executing a full domain check.
    This gives fast, responses, but there is also the option of
    providing a slower, no-cache response that carries out the full domain lookup.
    """

    # swagger_schema = None

    queryset = gc_models.GreenDomain.objects.all()
    serializer_class = gc_serializers.GreenDomainSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [AllowAny]
    lookup_field = "url"

    def list(self, request, *args, **kwargs):
        """
        Our override for bulk URL lookups, like an index/listing view
        """
        queryset = []
        urls = None

        get_url_params = self.request.query_params.getlist("urls")
        if get_url_params:
            urlstring, *_ = get_url_params
            urls = urlstring.split(",")

        # check for a payload. this takes precedence, to support large requests
        if self.request.data.get("urls"):
            urls = self.request.data.getlist("urls")

        if urls is not None:
            queryset = gc_models.GreenDomain.objects.filter(url__in=urls)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return response.Response(serializer.data)


    def response_for_greendomain(self, green_domain):
        """
        Format the greendomain object as the appropriate HTTP response
        """
        if green_domain.green:
            serializer = self.get_serializer(green_domain)
            return response.Response(serializer.data)
        else:
            return response.Response({
                "green": False, "url": green_domain.url, "data": False, "modified": green_domain.modified
            })


    def retrieve(self, request, *args, **kwargs):
        """
        Fetch entry matching the provided URL, like a 'detail' view
        """
        url = self.kwargs.get("url")

        # `nocache=true` is the same string used by nginx. Using the same params
        # means we won't have to worry about nginx caching our request before it
        # hits an app server
        skip_cache = request.GET.get("nocache") == "true"
        green_domain = gc_models.GreenDomain.green_domain_for(url, skip_cache)
        return self.response_for_greendomain(green_domain)

class BatchViewHelpers:
    """
    This is a base class for views which perform greenchecks over multiple domains simultaneously,
    containing shared logic and helpers.
    """

    def grey_urls_only(self, urls_list, queryset) -> list:
        """
        Accept a list of domain names, and a queryset of checked green
        domain objects, and return a list of only the grey domains.
        """
        green_list = [domain_object.url for domain_object in queryset]

        return [url for url in urls_list if url not in green_list]

    def build_green_greylist(self, grey_list: list, green_list) -> list:
        """
        Create a list of green and grey domains, to serialise and deliver.
        """
        from .models import GreenDomain

        grey_domains = []

        for domain in grey_list:
            gp = GreenDomain.grey_result(domain=domain)
            grey_domains.append(gp)

        evaluated_green_queryset = green_list[::1]

        return evaluated_green_queryset + grey_domains

    def response_for_urls_list(self, urls_list):
        if urls_list:
            queryset = gc_models.GreenDomain.objects.filter(url__in=urls_list)

        grey_list = self.grey_urls_only(urls_list, queryset)

        combined_batch_check_results = self.build_green_greylist(grey_list, queryset)

        serialized = gc_serializers.GreenDomainSerializer(
            combined_batch_check_results, many=True
        )

        return serialized

class LegacyMultiView(RetrieveAPIView, BatchViewHelpers):
    queryset = gc_models.GreenDomain.objects.all()
    serializer_class = gc_serializers.GreenDomainBatchSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [AllowAny]
    pagination_class = pagination.PageNumberPagination

    def retrieve(self, *args, **kwargs):
        """
        This is an undocumented legacy view which is still used by the browser extension - it
        accepts a JSON formatted list of URLS and returns an array of results.
        """
        try:
            urls = json.loads(kwargs["url_list"])
        except Exception:
            urls = []

        # fallback if the url list is not usable
        if urls is None:
            urls = []

        serialized = self.response_for_urls_list(urls)

        return response.Response(serialized.data)



class GreenDomainBatchView(CreateAPIView, BatchViewHelpers):
    """
    A batch API for checking domains in bulk, rather than individually.

    Upload a CSV file containing a list of domains, to get back the status of each domain.

    If you just want a list of green domains to check against, we publish a daily snapshot of all the green domains we have, for offline use and analysis, at https://datasets.thegreenwebfoundation.org
    """  # noqa

    queryset = gc_models.GreenDomain.objects.all()
    serializer_class = gc_serializers.GreenDomainBatchSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [AllowAny]
    pagination_class = pagination.PageNumberPagination
    parser_classes = [parsers.FormParser, parsers.MultiPartParser]
    renderer_classes = [drf_csv_rndr.CSVRenderer]


    def collect_urls(self, request: request.Request) -> list:
        """
        Accept a request object, parse any attached CSV file, and
        return a list of the valid domains in the file,
        """
        url_file = self.request.data.get("urls")
        # attachments are by default binary, so we need to
        # convert them to a format the CSV reader expects
        encoded_file = TextIOWrapper(url_file, encoding="utf-8")
        csv_file = csv.reader(encoded_file)

        urls_list = []

        for row in csv_file:
            if row is not None:
                url, *_ = row
                domain = tld.get_fld(url, fix_protocol=True)
                urls_list.append(domain)

        return urls_list


    def create(self, request, *args, **kwargs):
        """"""

        urls_list = self.collect_urls(request)

        logger.debug(f"urls_list: {urls_list}")

        serialized = self.response_for_urls_list(urls_list)

        headers = self.get_success_headers(serialized.data)

        return response.Response(serialized.data, headers=headers)

    def finalize_response(self, request, response, *args, **kwargs):
        """
        Override the default, so if we see a filename requested, send the
        header. This tells the client to treat it like a file to download,
        rather than trying to display it inline if using a browser.
        """
        filename = request.data.get("response_filename")
        if filename is not None:
            response["Content-Disposition"] = f"attachment; filename={filename}"

        return super().finalize_response(request, response, *args, **kwargs)
