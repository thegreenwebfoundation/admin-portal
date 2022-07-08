from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission

# This file lists the expected permissions for each group, and is used in a


def populate_group_permissions(apps, schema_editor):
    """
    Create the necessary groups and corresponding
    permissions for internal staff and external users of the
    admin platform
    """

    # create our groups, or make sure they exist
    # ACTIVE_GROUPS = {"admin": {}, "hostingprovider": {}, "datacenter": {}}

    HOSTING_PROVIDER_PERMS = [
        # need to add their own hosting provider and make updates
        "add_hostingprovider",
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
        # need to register their own datacenter and see it
        "add_datacenter",
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
    ]

    for app_config in apps.get_app_configs():
        # you need to models_module to True to go ahead with
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

