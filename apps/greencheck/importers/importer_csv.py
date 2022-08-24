import requests
import logging
import pandas as pd
import ipdb
import re
import ipaddress

from apps.greencheck.importers.importer_interface import BaseImporter, Importer

from django.conf import settings

logger = logging.getLogger(__name__)


class CsvImporter(BaseImporter):
    # def __init__(cls):
    # cls.hosting_provider_id = settings.Csv_PROVIDER_ID

    def fetch_data_from_source(cls):
        # TODO: fetch data from website dropping
        # For now: expect that a csv is saved somewhere and fetch in the following way:
        raw_data = pd.read_csv(
            "apps/greencheck/fixtures/test_dataset_csv.csv", header=None
        )
        return cls.parse_to_list(raw_data)

    def parse_to_list(cls, raw_data):
        try:
            list_of_ips = []

            validate_csv_file(raw_data)

            # Assume this single column holds ASN or network (ip with subnet)
            if len(raw_data.columns) == 1:
                list_of_ips = list(raw_data.iloc[:, 0])
            # elif len(data.columns) == 2:
            # start_ip = data.iloc[:,0]
            # end_ip = data.iloc[:,1]
            # Create network from these
            # for index, row in data.iterrows():
            #   list_of_ips.append(row[index,0])
            #     print(row['c1'], row['c2'])
            return list_of_ips
        except Exception as e:
            logger.exception("Something really unexpected happened. Aborting")

    def validate_csv_file(cls, data):
        # Loop through dataset to validate the data format
        if len(data.columns) == 1:
            validate_column_in_csv_file(data)
        elif len(data.columns) == 2:
            validate_column_in_csv_file(data.iloc[:, 0])
            validate_column_in_csv_file(data.iloc[:, 1])
        else:
            # exception: wrong format
            logger.exception("Number of columns in CSV are not as expected")

    def validate_column_in_csv_file(cls, column):
        column = list(column)
        for address in column:
            if not re.search("(AS)[0-9]+$", address) or not isinstance(
                ipaddress.ip_network(address),
                (ipaddress.IPv4Network, ipaddress.IPv6Network),
            ):
                logger.exception("Value of %s is in an incorrect format", address)
