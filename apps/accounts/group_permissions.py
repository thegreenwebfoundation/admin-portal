from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission

# This file lists the expected permissions for each group.
# We use it when setting up tests, and for keeping permissions
# in source control to avoid drift

# create our groups, or make sure they exist
# ACTIVE_GROUPS = {"admin": {}, "hostingprovider": {}, "datacenter": {}}

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
    "change_greencheckasn",
    "view_greencheckasn",
    "view_greencheckasnapprove",
    # hosters should be able to see the status of IP requests and approvals
    "add_greencheckip",
    "change_greencheckip",
    "view_greencheckip",
    "view_greencheckipapprove",
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

ADMIN_PERMS = [
    # needed to be able to add hosting providers and data centers
    "add_hostingprovider",
    "add_datacenter",
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
]


def populate_group_permissions(apps, schema_editor):
    """
    Create the necessary groups and corresponding
    permissions for internal staff and external users of the
    admin platform
    """

    for app_config in apps.get_app_configs():
        # you need to set models_module to True to go ahead with
        # setting up the required permissions
        app_config.models_module = True
        # get or create all the permissions for all the models listed
        # in the app content types
        create_permissions(app_config, verbosity=0)
        # reset after change made
        app_config.models_module = None

    # fetch all perms
    all_perms = Permission.objects.all()

    # add our perms for hosting provider
    hostingprovider, _ = Group.objects.get_or_create(name="hostingprovider")
    hoster_perms = [
        perm for perm in all_perms if perm.codename in HOSTING_PROVIDER_PERMS
    ]
    hostingprovider.permissions.add(*hoster_perms)

    # then do the datacenter group
    datacenter, _ = Group.objects.get_or_create(name="datacenter")
    datacenter_perms = [perm for perm in all_perms if perm.codename in DATACENTER_PERMS]
    datacenter.permissions.add(*datacenter_perms)

    # finally our admin group
    admin, _ = Group.objects.get_or_create(name="admin")
    admin_perms = [perm for perm in all_perms if perm.codename in ADMIN_PERMS]
    admin.permissions.add(*admin_perms)


def populate_group_permissions_2022_08_05(apps, schema_editor):
    """
    Update the permissions so that the admin group has all the permissions
    of the hosting provider and datacentre groups. This saves us needing to
    add a user to multiple groups, and lets us filter by group more
    effectively in audit logs.
    """

    for app_config in apps.get_app_configs():
        # you need to set models_module to True to go ahead with
        # setting up the required permissions
        app_config.models_module = True
        # get or create all the permissions for all the models listed
        # in the app content types
        create_permissions(app_config, verbosity=0)
        # reset after change made
        app_config.models_module = None

    # fetch all perms
    all_perms = Permission.objects.all()

    # all the permissions should lie with our admin groups
    admin, _ = Group.objects.get_or_create(name="admin")
    admin_perms = [perm for perm in all_perms if perm.codename in ADMIN_PERMS]
    datacenter_perms = [perm for perm in all_perms if perm.codename in DATACENTER_PERMS]
    hoster_perms = [
        perm for perm in all_perms if perm.codename in HOSTING_PROVIDER_PERMS
    ]

    # make sure our admins all the same perms, so we aren't reliant on group membership
    admin.permissions.add(*admin_perms)
    admin.permissions.add(*datacenter_perms)
    admin.permissions.add(*hoster_perms)


def group_permissions_2022_10_28_provider_request_add(apps, schema_editor):
    """
    Explicitly grant all permissions for provider_request to the admin group
    """

    admin, _ = Group.objects.get_or_create(name="admin")
    pr_perms_codenames = [
        "add_providerrequest",
        "change_providerrequest",
        "view_providerrequest",
    ]
    pr_perms = Permission.objects.filter(codename__in=pr_perms_codenames)

    admin.permissions.add(*pr_perms)


def group_permissions_2022_10_28_provider_request_revert(apps, schema_editor):
    """
    Explicitly revert all permissions for provider_request to the admin group
    """

    admin, _ = Group.objects.get_or_create(name="admin")
    pr_perms_codenames = [
        "add_providerrequest",
        "change_providerrequest",
        "view_providerrequest",
    ]
    pr_perms = Permission.objects.filter(codename__in=pr_perms_codenames)

    admin.permissions.remove(*pr_perms)


def group_permissions_2023_04_26_disallow_adding_hp_and_dc(apps, schema_editor):
    """
    We no longer allow adding new Hostingprovider and Datacenter objects by non-staff users.
    These permissions are explicitly moved to the "admin" group
    """
    pr_perms_codenames = [
        "add_hostingprovider",
        "add_datacenter",
    ]
    pr_perms = Permission.objects.filter(codename__in=pr_perms_codenames)

    hp, _ = Group.objects.get_or_create(name="hostingprovider")
    dc, _ = Group.objects.get_or_create(name="datacenter")
    admin, _ = Group.objects.get_or_create(name="admin")

    hp.permissions.remove(*pr_perms)
    dc.permissions.remove(*pr_perms)
    admin.permissions.add(*pr_perms)


def group_permissions_2023_04_26_revert_disallow_adding_hp_and_dc(apps, schema_editor):
    """
    Reverts group_permissions_2023_04_26_disallow_adding_hp_and_dc
    """
    pr_perms_codenames = [
        "add_hostingprovider",
        "add_datacenter",
    ]
    pr_perms = Permission.objects.filter(codename__in=pr_perms_codenames)

    hp, _ = Group.objects.get_or_create(name="hostingprovider")
    dc, _ = Group.objects.get_or_create(name="datacenter")

    hp.permissions.add(*pr_perms)
    dc.permissions.add(*pr_perms)

def group_permissions_2025_05_12_add_verification_basis_permissions_for_admins(apps, schema_editor):
    """
    Gives admins permission to modify bases for verification.
    """
    pr_perms_codenames = [
        "add_verificationbasis",
        "change_verificationbasis",
        "view_verificationbasis",
        "delete_verificationbasis"
    ]

    pr_perms = Permission.objects.filter(codename__in=pr_perms_codenames)

    admin, _ = Group.objects.get_or_create(name="admin")

    admin.permissions.add(*pr_perms)
