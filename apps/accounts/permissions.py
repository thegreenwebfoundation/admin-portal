from dataclasses import dataclass


"""
Definitions for object-level permissions for the `accounts` app.
"""


@dataclass
class Permission:
    codename: str
    full_name: str
    description: str

    def astuple(self):
        return (self.codename, self.description)

    def __str__(self):
        return self.full_name


manage_provider = Permission(
    "manage_provider", "accounts.manage_provider", "Manage provider"
)
manage_datacenter = Permission(
    "manage_datacenter", "accounts.manage_datacenter", "Manage datacenter"
)