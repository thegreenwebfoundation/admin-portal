import csv
import logging
import socket
import json
import pika
import dramatiq
from io import TextIOWrapper

import tld
import urllib
from django.utils import timezone
from django.conf import settings
from rest_framework import pagination, parsers, request, response, viewsets
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema  # noqa

# flake8 doesn't like rest_framework_csv. It's not clear why
from rest_framework_csv import renderers as drf_csv_rndr  # noqa

from .api.ip_range_viewset import IPRangeViewSet  # noqa
from .api.asn_viewset import ASNViewSet  # noqa

# from ...accounts.models import ac_models
from . import models as gc_models
from . import serializers as gc_serializers

# import (
# from .serializers import (
#     gc_serializers.GreenDomainBatchSerializer,
#     gc_serializers.GreenDomainSerializer,
# )
from .domain_check import GreenDomainChecker


logger = logging.getLogger(__name__)


checker = GreenDomainChecker()


def log_domain_safely(domain):
    from .tasks import process_log

    try:
        process_log.send(domain)
    except (
        pika.exceptions.AMQPConnectionError,
        dramatiq.errors.ConnectionClosed,
    ):
        logger.warn("RabbitMQ not available, not logging to RabbitMQ")
    except Exception as err:
        logger.exception(f"Unexpected error of type {err}")


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

    checker = GreenDomainChecker()

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

    def legacy_grey_response(self, domain: str, log_check=True):
        """
        Return the response we historically send when
        a check doesn't return a green result.
        """

        if log_check:
            log_domain_safely(domain)
        return response.Response({"green": False, "url": domain, "data": False})

    def return_green_response(self, instance, log_check=True):
        """
        Return the response we historically made when returning
        a green result
        """

        if log_check:
            log_domain_safely(instance.url)
        serializer = self.get_serializer(instance)
        return response.Response(serializer.data)

    def build_response_from_cache(self, instance, log_check=True):
        """
        Return the response we historically made when returning
        a green result
        """

        if log_check:
            log_domain_safely(instance.url)
        serializer = self.get_serializer(instance)
        return response.Response(serializer.data)

    def build_response_from_full_network_lookup(self, domain):
        """
        Build a response
        """
        try:
            res = checker.perform_full_lookup(domain)
            if res.green:
                return self.return_green_response(res)
        except socket.gaierror:
            return self.legacy_grey_response(domain)
        except UnicodeError:
            return self.legacy_grey_response(domain)

    def build_response_from_database_lookup(self, domain):
        instance = gc_models.GreenDomain.objects.filter(url=domain).first()
        if instance:
            return self.return_green_response(instance)

    def clear_from_caches(self, domain):
        """
        Clear any trace of a domain from local caches.
        """

        # we don't delete entries that have been updated
        # via a carbon.txt file, but we need to check it exists first
        if fetched_domain := gc_models.GreenDomain.objects.filter(url=domain).first():
            #
            if fetched_domain.hosting_provider.counts_as_green():
                return

            fetched_domain.delete()

    def retrieve(self, request, *args, **kwargs):
        """
        Fetch entry matching the provided URL, like a 'detail' view
        """
        url = self.kwargs.get("url")
        domain = None

        # `nocache=true` is the same string used by nginx. Using the same params
        # means we won't have to worry about nginx caching our request before it
        # hits an app server
        skip_cache = request.GET.get("nocache") == "true"

        try:
            domain = self.checker.validate_domain(url)
        except Exception:
            # not a valid domain, OR a valid IP. Get rid of it.
            logger.warning(f"unable to extract domain from {url}")
            return self.legacy_grey_response(url, log_check=False)

        if skip_cache:
            # try to fetch domain the long way, clearing it from the
            # any caches if already present
            try:
                gd = gc_models.GreenDomain
                provider = gd.objects.get(url=domain).hosting_provider
            except Exception:
                import ipdb

                ipdb.set_trace()

            if provider:
                if "green:carbontxt" not in provider.staff_labels.names():
                    provider.staff_labels.slugs()
                    self.clear_from_caches(domain)
            else:
                self.clear_from_caches(domain)

            # self.clear_from_caches(domain)

            if http_response := self.build_response_from_full_network_lookup(domain):
                return http_response

        # not in the cache. Try the database instead:
        if http_response := self.build_response_from_database_lookup(domain):
            return http_response

        # not in database or the cache, try full lookup using network
        if http_response := self.build_response_from_full_network_lookup(domain):
            return http_response

        # not in database or the cache, nor can we see find it with
        # any third party lookups. Fall back to saying we couldn't find anything,
        # the way the API used to work.
        return self.legacy_grey_response(url)


class GreenDomainBatchView(CreateAPIView):
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

        if urls_list:
            queryset = gc_models.GreenDomain.objects.filter(url__in=urls_list)

        grey_list = checker.grey_urls_only(urls_list, queryset)

        combined_batch_check_results = checker.build_green_greylist(grey_list, queryset)

        serialized = gc_serializers.GreenDomainSerializer(
            combined_batch_check_results, many=True
        )

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
