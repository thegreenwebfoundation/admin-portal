import logging

from rest_framework import permissions
from rest_framework import permissions

logger = logging.getLogger(__name__)


class BelongsToHostingProvider(permissions.BasePermission):
    """
    If a user belongs to the hosting provider they are allowed
    to update the object
    """

    def has_object_permission(self, request, view, obj):
        """
        Users should only be able to update the object if the hosting
        provider associated with it is the same as their one they are
        part of
        """
        return bool(
            request.method in permissions.SAFE_METHODS
            or request.user
            and obj.hostingprovider == request.user.hostingprovider
        )

