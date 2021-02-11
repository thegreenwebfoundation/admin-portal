import csv
import logging
from io import TextIOWrapper

import tld
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import (
    pagination,
    parsers,
    request,
    response,
    viewsets,
)
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.settings import api_settings
from rest_framework_csv import renderers as drf_csv_rndr

from .models import GreencheckIp, GreenPresenting
from .serializers import (
    GreenDomainBatchSerializer,
    GreenDomainSerializer,
    GreenIPRangeSerializer,
)

logger = logging.getLogger(__name__)


class IPRangeViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list` and `retrieve` actions.
    """

    serializer_class = GreenIPRangeSerializer
    queryset = GreencheckIp.objects.all()

    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def filter_queryset(self, queryset):
        """
        Because our viewset takes care of pagination and the rest
        all we change is what is returned when we filter the queryset
        for a given user.

        http://www.cdrf.co/3.9/rest_framework.viewsets/ModelViewSet.html#list
        """

        user = self.request.user

        if user is not None:
            provider = self.request.user.hostingprovider

            if provider is not None:
                return provider.greencheckip_set.filter(active=True)

        return []

    def perform_destroy(self, instance):
        """
        Overriding this one function means that the rest of
        our destroy method works as expected.
        """
        instance.active = False
        instance.save()


class GreenDomainViewset(viewsets.ReadOnlyModelViewSet):
    """
    The greencheck service to replicate the older PHP API for checking domains.

    Supports the same single and batch API.

    By default serves a response
    from the GreenDomains table, rather than executing a full domain check.
    This gives fast, responses, but there is also the option of
    providing a slower, no-cache response that carries out the full domain lookup.
    """

    queryset = GreenPresenting.objects.all()
    serializer_class = GreenDomainSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [AllowAny]
    lookup_field = "url"

    def list(self, request, *args, **kwargs):
        """
        Our override for bulk URL lookups, like an index/listing view
        """
        queryset = []
        urls = self.request.query_params.getlist("urls")

        # check for a payload. this takes precedence, to support large requests
        if self.request.data.get("urls"):
            urls = self.request.data.get("urls")

        if urls is not None:
            queryset = GreenPresenting.objects.filter(url__in=urls)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return response.Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        Fetch entry matching the provided URL, like an 'detail' view
        """
        url = self.kwargs.get("url")
        instance = get_object_or_404(GreenPresenting, url=url)
        serializer = self.get_serializer(instance)
        return response.Response(serializer.data)


class GreenDomainBatchView(CreateAPIView):
    """
    A batch API for making buik requests, by POSTing a file
    comprised of a list of domains.
    """

    queryset = GreenPresenting.objects.all()
    serializer_class = GreenDomainBatchSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [AllowAny]
    pagination_class = pagination.PageNumberPagination
    parser_classes = [parsers.FormParser, parsers.MultiPartParser]
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES + [
        drf_csv_rndr.CSVRenderer
    ]

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

    def build_green_greylist(self, grey_list: list, green_list) -> list:
        """
        Create a list of geeen and grey domains, to serialise and deliver.


        """
        grey_domains = []

        for domain in grey_list:
            gp = GreenPresenting(url=domain)
            gp.hosted_by = None
            gp.hosted_by_id = None
            gp.hosted_by_website = None
            gp.partner = False
            gp.modified = timezone.now()
            grey_domains.append(gp)

        evaluated_green_queryset = green_list[::1]

        return evaluated_green_queryset + grey_domains

    def grey_urls_only(self, urls_list, queryset) -> list[str]:
        """
        Accept a list of domain names, and a queryset of checked green
        domain objects, and return a list of only the grey domains.
        """
        green_list = [domain_object.url for domain_object in queryset]

        return [url for url in urls_list if url not in green_list]

    def create(self, request, *args, **kwargs):
        """
        """

        urls_list = self.collect_urls(request)

        logger.debug(f"urls_list: {urls_list}")

        if urls_list:
            queryset = GreenPresenting.objects.filter(url__in=urls_list)

        grey_list = self.grey_urls_only(urls_list, queryset)

        combined_batch_check_results = self.build_green_greylist(grey_list, queryset)

        serialized = GreenDomainSerializer(combined_batch_check_results, many=True)

        headers = self.get_success_headers(serialized.data)

        return response.Response(serialized.data, headers=headers)
