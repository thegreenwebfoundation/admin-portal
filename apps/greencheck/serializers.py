import ipaddress

from rest_framework import serializers

from apps.accounts.models import Hostingprovider

from .models import GreencheckIp


class IPDecimalField(serializers.DecimalField):
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


class UserFilteredPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        request = self.context.get("request", None)
        queryset = super(UserFilteredPrimaryKeyRelatedField, self).get_queryset()
        if not request or not queryset:
            return None
        return queryset.filter(user=request.user)


class GreenIPRangeSerializer(serializers.ModelSerializer):

    ip_start = IPDecimalField(max_digits=39, decimal_places=0)
    ip_end = IPDecimalField(max_digits=39, decimal_places=0)
    hostingprovider = UserFilteredPrimaryKeyRelatedField(
        queryset=Hostingprovider.objects.all()
    )

    def validate(self, data):
        """
        Check that start is before finish.
        """

        start = data["ip_start"]
        end = data["ip_end"]
        if start > end:
            raise serializers.ValidationError(
                "The IP range must start with a lower IP than the end IP"
            )
        return data

    class Meta:
        model = GreencheckIp
        fields = ["ip_start", "ip_end", "hostingprovider", "id"]
