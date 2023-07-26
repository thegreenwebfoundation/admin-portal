import logging

from rest_framework import permissions

logger = logging.getLogger(__name__)


class UserManagesHostingProvider(permissions.BasePermission):
    """
    Check object-level permissions to decide if User can manage Hostingprovider
    """

    def _has_permission(self, request, hp_id):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user and request.user.is_authenticated:
            return request.user.hosting_providers.filter(id=hp_id).exists()
        return False

    def has_object_permission(self, request, view, obj):
        """
        Check permissions when updating the object
        """
        return self._has_permission(request, obj.hostingprovider.id)

    def has_permission(self, request, view):
        """
        Check permissions when creating a new object (POST request),
        otherwise return True to rely on a consecutive call to has_object_permission.
        """
        if request.method == "POST":
            return self._has_permission(request, request.data.get("hostingprovider"))
        return True
