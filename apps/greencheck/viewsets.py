import logging
import csv
from rest_framework import viewsets
from rest_framework import generics
from rest_framework import status
from rest_framework import pagination
from rest_framework import parsers
from django.shortcuts import get_object_or_404
from .serializers import (
    GreenIPRangeSerializer,
    GreenDomainSerializer,
    GreenDomainBatchSerializer,
)
from io import TextIOWrapper
from .models import GreencheckIp, Hostingprovider, GreenPresenting
from rest_framework import response
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import CreateAPIView

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

    def create(self, request, *args, **kwargs):
        """
        """
        url_file = self.request.data.get("urls")
        f = TextIOWrapper(url_file, encoding="utf-8")

        csv_file = csv.reader(f)
        urls_list = []

        for row in csv_file:
            logger.info(row)
            if row:
                url, *_ = row
                urls_list.append(url)

        if urls_list:
            queryset = GreenPresenting.objects.filter(url__in=urls_list)

        serializer = GreenDomainSerializer
        srs = serializer(queryset, many=True)
        headers = self.get_success_headers(srs.data)

        return response.Response(srs.data, headers=headers)
