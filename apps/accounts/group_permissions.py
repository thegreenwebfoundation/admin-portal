from django.contrib.auth.models import Group, Permission

# This file lists the expected permissions for each group.
# We use it when setting up tests, and for keeping permissions
# in source control to avoid drift

HOSTING_PROVIDER_PERMS = [
    # needed to make updates
    "change_hostingprovider",
    "view_hostingprovider",
    # hosting provider certificates are
    "add_hostingprovidercertificate",
    "change_hostingprovidercertificate",
    "delete_hostingprovidercertificate",
    "view_hostingprovidercertificate",
    # need to be able to link providers to datacenters
    "add_hostingproviderdatacenter",
    "change_hostingproviderdatacenter",
    "delete_hostingproviderdatacenter",
    "view_hostingproviderdatacenter",
    # need to be able to add supporting evidence and delete own documents
    "add_hostingprovidersupportingdocument",
    "change_hostingprovidersupportingdocument",
    "delete_hostingprovidersupportingdocument",
    "view_hostingprovidersupportingdocument",
    # need to change and view own user
    "change_user",
    "view_user",
    # hosters should be able to see the status of ASN requests and approvals
    "add_greencheckasn",
    "delete_greencheckasn",
    "view_greencheckasn",
    "view_greencheckasnapprove",
    # hosters should be able to see the status of IP requests and approvals
    "add_greencheckip",
    "delete_greencheckip",
    "view_greencheckip",
    "view_greencheckipapprove",
    "add_providerrequestiprange",
]

DATACENTER_PERMS = [
    # needed to view and modify own datacenters
    "change_datacenter",
    "view_datacenter",
    # need to add and see provided links to legacy certificates
    "add_datacentercertificate",
    "change_datacentercertificate",
    "delete_datacentercertificate",
    "view_datacentercertificate",
    # legacy information - less need to list it
    "add_datacenterclassification",
    "change_datacenterclassification",
    "delete_datacenterclassification",
    "view_datacenterclassification",
    # legacy information - less need to list it
    "add_datacentercooling",
    "change_datacentercooling",
    "delete_datacentercooling",
    "view_datacentercooling",
    # need to be able to add, and remove own supporting evidence for datacentres
    "add_datacentersupportingdocument",
    "change_datacentresupportingdocument",
    "delete_datacentresupportingdocument",
    "view_datacentresupportingdocument",
]

ADMIN_PERMS= [
    # Can administer API logs
    "add_apilogsmodel",
    "change_apilogsmodel",
    "delete_apilogsmodel",
    "view_apilogsmodel",
    # Can administer flags
    "add_flag",
    "change_flag",
    "delete_flag",
    "view_flag",
    # Can administer services
    "add_service",
    "change_service",
    "delete_service",
    "view_service",
    # Can add, edit, and view provider requests
    "add_providerrequest",
    "change_providerrequest",
    "view_providerrequest",
    # needed to be able to add hosting providers and data centers
    "add_hostingprovider",
    "add_datacenter",
    "manage_datacenter",
    "manage_provider",
    # need to be able to add, remove and change users,
    "add_user",
    "change_user",
    "delete_user",
    "view_user",
    # need access to log entries,
    "add_logentry",
    "view_logentry",
    # need to be able to see greenchecks,
    "delete_greencheck",
    "view_greencheck",
    # need to see status of Green ASNs,
    "add_greencheckasn",
    "change_greencheckasn",
    "delete_greencheckasn",
    "view_greencheckasn",
    # need full access to AS approvals,
    "add_greencheckasnapprove",
    "change_greencheckasnapprove",
    "delete_greencheckasnapprove",
    "view_greencheckasnapprove",
    # need full access to Green IPs,
    "add_greencheckip",
    "change_greencheckip",
    "delete_greencheckip",
    "view_greencheckip",
    # need full access to Green IP Approvals,
    "add_greencheckipapprove",
    "change_greencheckipapprove",
    "delete_greencheckipapprove",
    "view_greencheckipapprove",
    # need to be able to see support messages and create new ones
    "add_supportmessage",
    "change_supportmessage",
    "delete_supportmessage",
    "view_supportmessage",
    # need to be able to add internal notes for hosting providers and datacentres
    "add_datacenternote",
    "change_datacenternote",
    "delete_datacenternote",
    "view_datacenternote",
    "add_hostingprovidernote",
    "change_hostingprovidernote",
    "delete_hostingprovidernote",
    "view_hostingprovidernote",
    # need to be able to edit labels used by staff for annotating providers
    "add_label",
    "change_label",
    "delete_label",
    "view_label",
    # need to be able to edit the tags used for listing the services that
    # providers offer
    "add_tag",
    "change_tag",
    "delete_tag",
    "view_tag",
    "add_taggeditem",
    "change_taggeditem",
    "delete_taggeditem",
    "view_taggeditem",
    ## Can add and update the bases for verification listed in the onboarding wizard
    "add_verificationbasis",
    "change_verificationbasis",
    "view_verificationbasis",
    "delete_verificationbasis",
    ## Can administer linked domains
    "add_linkeddomain",
    "change_linkeddomain",
    "view_linkeddomain",
    "delete_linkeddomain",
    ## Can administer greendomains
    "add_greendomain",
    "change_greendomain",
    "view_greendomain",
    "delete_greendomain",
    # Can administer datacenter locations
    "add_datacenterlocation",
    "change_datacenterlocation",
    "delete_datacenterlocation",
    "view_datacenterlocation",
]

PERMS = {
    "hostingprovider": set(HOSTING_PROVIDER_PERMS),
    "datacenter": set(DATACENTER_PERMS),
    "admin": set(HOSTING_PROVIDER_PERMS + DATACENTER_PERMS + ADMIN_PERMS),
}


def populate_group_permissions(_apps=None, _schema_editor=None, logger=None):
    """
    Idempotently update group permissions to ensure that all the permissons listed above
    are applied to the corect groups, and any extraneous permissions are deleted.
    Can optionally be passed a callable as "logger" in order to print a summary of changes.
    The unused _apps and _schema_editor arguments are to support the legacy use of this method,
    where it was called in a RunPython migration action.
    """
    all_perms = Permission.objects.all()

    for group_key in PERMS:
        group, _ = Group.objects.get_or_create(name=group_key)
        old_perm_names = set([perm.codename for perm in group.permissions.all()])
        group.permissions.clear()
        new_group_perms = [perm for perm in all_perms if perm.codename in PERMS[group_key]]
        group.permissions.add(*new_group_perms)
        if logger:
            new_perm_names = set([perm.codename for perm in new_group_perms])
            added_perm_names = new_perm_names - old_perm_names
            removed_perm_names = old_perm_names - new_perm_names
            if len(added_perm_names) > 0 or len(removed_perm_names) > 0:
                logger(f" - Added {len(added_perm_names)} permissions, and removed {len(removed_perm_names)} permissions for group {group_key}.")
                if len(added_perm_names) > 0:
                    added_perm_names_string = ", ".join(added_perm_names)
                    logger(f"   - Added: {added_perm_names_string}")
                if len(removed_perm_names) > 0:
                    removed_perm_names_string = ", ".join(removed_perm_names)
                    logger(f"   - Removed: {removed_perm_names_string}")
            else:
                logger(f"Permissions for group {group_key} up to date.")


# All the below method definitions are now no-ops - the above definition deprecates them.
# We keep the old definitions around as they are still called from within migrations.

def populate_group_permissions_2022_08_05(apps, schema_editor):
    """
    Update the permissions so that the admin group has all the permissions
    of the hosting provider and datacentre groups. This saves us needing to
    add a user to multiple groups, and lets us filter by group more
    effectively in audit logs.
    """
    # This is now decleratively set in populate_group_permissions, we keep this method
    # here as a no-op, as it is called from within migrations which still get run
    # on initializing a new database.
    pass


def group_permissions_2022_10_28_provider_request_add(apps, schema_editor):
    """
    Explicitly grant all permissions for provider_request to the admin group
    """
    # This is now decleratively set in populate_group_permissions, we keep this method
    # here as a no-op, as it is called from within migrations which still get run
    # on initializing a new database.
    pass


def group_permissions_2022_10_28_provider_request_revert(apps, schema_editor):
    """
    Explicitly revert all permissions for provider_request to the admin group
    """
    # Permissions are no longer set in migrations, so revert steps are not needed.
    # However, we keep this around as a no-op to prevent errors in case the migrations
    # that call it are ever called.
    pass


def group_permissions_2023_04_26_disallow_adding_hp_and_dc(apps, schema_editor):
    """
    We no longer allow adding new Hostingprovider and Datacenter objects by non-staff users.
    These permissions are explicitly moved to the "admin" group
    """
    # This is now decleratively set in populate_group_permissions, we keep this method
    # here as a no-op, as it is called from within migrations which still get run
    # on initializing a new database.
    pass


def group_permissions_2023_04_26_revert_disallow_adding_hp_and_dc(apps, schema_editor):
    """
    Reverts group_permissions_2023_04_26_disallow_adding_hp_and_dc
    """
    # Permissions are no longer set in migrations, so revert steps are not needed.
    # However, we keep this around as a no-op to prevent errors in case the migrations
    # that call it are ever called.
    pass

def group_permissions_2025_05_12_add_verification_basis_permissions_for_admins(apps, schema_editor):
    """
    Gives admins permission to modify bases for verification.
    """
    # This is now decleratively set in populate_group_permissions, we keep this method
    # here as a no-op, as it is called from within migrations which still get run
    # on initializing a new database
    pass

def group_permissions_2025_06_03_add_linked_domain_permissions_for_admins(apps, schema_editor):
    """
    Gives admins permission to modify linked domains
    """
    # This is now decleratively set in populate_group_permissions, we keep this method
    # here as a no-op, as it is called from within migrations which still get run
    # on initializing a new database
    pass
