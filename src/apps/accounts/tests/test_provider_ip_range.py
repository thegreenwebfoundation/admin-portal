import pytest
from ..models import ProviderRequest, ProviderRequestIPRange

# add import for django validation error
from django.core.exceptions import ValidationError


@pytest.fixture
def ip_range():
    return ProviderRequestIPRange()


@pytest.mark.parametrize(
    "start_ip,end_ip,expected_size",
    [
        # IPv4 test cases
        ("192.168.1.1", "192.168.1.1", 1),  # Single IP
        ("192.168.1.1", "192.168.1.10", 10),  # Small range
        ("192.168.1.0", "192.168.1.255", 256),  # Full subnet
        ("10.0.0.0", "10.0.1.0", 257),  # Across subnet boundary
        # IPv6 test cases
        ("2001:db8::1", "2001:db8::1", 1),  # Single IP
        ("2001:db8::1", "2001:db8::10", 16),  # Small range
        ("2001:db8::0", "2001:db8::ff", 256),  # Larger range
        # Edge cases
        ("0.0.0.0", "0.0.0.255", 256),  # Start of IPv4 range
        ("255.255.255.0", "255.255.255.255", 256),  # End of IPv4 range
    ],
)
def test_ip_range_size_calculation(ip_range, start_ip, end_ip, expected_size):
    ip_range.start = start_ip
    ip_range.end = end_ip
    assert ip_range.ip_range_size() == expected_size


def test_ip_range_size_with_empty_values(ip_range):
    # Test with no values set
    assert ip_range.ip_range_size() == 0

    # Test with only start IP
    ip_range.start = "192.168.1.1"
    assert ip_range.ip_range_size() == 0

    # Test with only end IP
    ip_range.start = None
    ip_range.end = "192.168.1.10"
    assert ip_range.ip_range_size() == 0


# @pytest.mark.django_db
# def test_full_model_creation():
#     """Test creating and saving a model instance"""
#     provider_request = ProviderRequest.objects.create()  # Add necessary fields
#     ip_range = ProviderRequestIPRange.objects.create(
#         start="192.168.1.1", end="192.168.1.10", request=provider_request
#     )
#     assert ip_range.ip_range_size() == 10
#     assert str(ip_range) == "192.168.1.1 - 192.168.1.10"


@pytest.mark.parametrize(
    "start_ip,end_ip",
    [
        ("192.168.1.10", "192.168.1.1"),  # End IP before start IP
        ("invalid_ip", "192.168.1.1"),  # Invalid IP format
        ("192.168.1.1", "invalid_ip"),  # Invalid IP format
        ("2001:db8::1", "192.168.1.1"),  # Mixed IPv6 and IPv4
    ],
)
def test_invalid_ip_ranges(ip_range, start_ip, end_ip):
    ip_range.start = start_ip
    ip_range.end = end_ip
    with pytest.raises(ValidationError):
        ip_range.clean()
