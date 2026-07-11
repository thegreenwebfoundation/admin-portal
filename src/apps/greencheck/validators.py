import ipaddress
from typing import Union
from django.core import exceptions

IpAddress = Union[str, int]


def validate_ip_range(ip_start: IpAddress, ip_end: IpAddress) -> None:
    """
    Validation logic for IP range:
    do not allow ip_start to be after ip_end.

    """
    start_ip = ipaddress.ip_address(ip_start)
    end_ip = ipaddress.ip_address(ip_end)
    if start_ip > end_ip:
        raise exceptions.ValidationError(
            "IP range invalid! IP start must be before IP end", code="invalid"
        )
