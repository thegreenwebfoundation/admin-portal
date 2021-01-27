from rest_framework import serializers
from .models import GreencheckIp

import ipaddress

class IpDecimalField(serializers.DecimalField):
    """
    A TGWF specific decimal field to account for the fact that
    we represent an IP address internall wth MySQL as a Decimal
    type, but we exposes it as a set of octets for ipv4, and
    an ipv6 representation
    """

    def to_representation(self, instance):
        """
        Convert a string or integer based ip
        address, and convert to a readable
        string.
        """
        addr = ipaddress.ip_address(instance)
        return str(addr)

    def to_internal_value(self, data):
        """
        Convert a octet based ip address into
        a native python ip address
        """
        addr = ipaddress.ip_address(data)
        return addr


class GreenIPRange(serializers.ModelSerializer):

    ip_start = IpDecimalField(max_digits=39, decimal_places=0)
    ip_end = IpDecimalField(max_digits=39, decimal_places=0)

    class Meta:
        model = GreencheckIp
        fields = ['active', "ip_start", "ip_end", "hostingprovider"]



