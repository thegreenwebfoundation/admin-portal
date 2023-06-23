from dataclasses import dataclass


@dataclass
class Permission:
    """
    This data class provides attributes and methods
    for the expected representations of object-level permissions in the "accounts" app.

    It is entirely independent of django.contrib.auth.models.Permission.

    The purpose of this data class is to be used in various places in the code
    (migrations, views, tests) that expect a a permission in various representations.
    As an example:
    - guardian.shortcuts methods assign_perm and remove_perm expect the codename of the permission as an argument
    if the content type of the object can be determined, or full permission name otherwise.
    We can pass `permissions.manage_provider.codename` or `permissions.manage_provider.full_name`
    instead of passing strings: "manage_provider" or "accounts.manage_provider"

    The actual object-level permission (based on django.contrib.auth.models.Permission)
    is created by django-guardian when it picks up the definition of the `Meta` class
    of a given model.
    """

    codename: str
    full_name: str
    description: str

    def astuple(self):
        return (self.codename, self.description)

    def __str__(self):
        return self.full_name


"""
Definitions for object-level permissions for the `accounts` app
"""

manage_provider = Permission(
    "manage_provider", "accounts.manage_provider", "Manage provider"
)
manage_datacenter = Permission(
    "manage_datacenter", "accounts.manage_datacenter", "Manage datacenter"
)
