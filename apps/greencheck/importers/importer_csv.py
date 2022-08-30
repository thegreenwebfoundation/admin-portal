import requests
import logging
import pandas as pd
import ipdb
import re
import ipaddress
import rich

from apps.greencheck.importers.importer_interface import BaseImporter, Importer

from django.conf import settings

logger = logging.getLogger(__name__)


class CsvImporter(BaseImporter):
    # def __init__(cls):
        
        
    # cls.hosting_provider_id = settings.Csv_PROVIDER_ID

    def fetch_data_from_source(cls, filepath_or_buffer):
        raw_data = pd.read_csv(
            filepath_or_buffer, header=None
        )
        return cls.parse_to_list(raw_data)

    def parse_to_list(cls, raw_data):
        rows = raw_data.values
        imported_networks  = {
            "asns": [],
            "ip_networks": [],
            "ip_ranges": []            
        }
        for row in rows:
                
            # just one column? it's probably an AS or a IP network
            if pd.isnull(row[1]):
            
                # is it a AS number?
                if row[0].startswith("AS"):
                    # as_number = row[0].split("AS ")[1]
                    imported_networks["asns"].append(row[0])
                else: 
                    # if it isn't an AS number it's probably an IP network
                    try:
                        ip_network = ipaddress.ip_network(row[0])
                        imported_networks['ip_networks'].append(row[0])
                    except Exception:
                        logger.warn(f"Item {row[0]} was not an ip network. Not importing.")
            else:
                # import ipdb ; ipdb.set_trace()                    
                try:
                    first_ip, last_ip = row[0].strip(), row[1].strip()
                    ip_begin = ipaddress.ip_address(first_ip)
                    ip_end = ipaddress.ip_address(last_ip)
                    imported_networks['ip_ranges'].append((first_ip, last_ip))
                except Exception:
                    logger.warn(f"Row {row} does not look like an IP address. Not importing")
                
        flattened_network_list = [
            *imported_networks['asns'], 
            *imported_networks['ip_networks'],
            *imported_networks['ip_ranges']
        ]
        rich.print(flattened_network_list)
        
        return flattened_network_list
        
        


