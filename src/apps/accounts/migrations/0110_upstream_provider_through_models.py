import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
from django.db import migrations, models

from ..group_permissions import populate_group_permissions


def copy_existing_upstream_connections(apps, schema_editor):
    """
    Copy rows from the auto-generated M2M through tables into the new
    explicit through models, defaulting is_public=True so existing
    connections remain visible in the public directory.
    """
    UpstreamProvider = apps.get_model("accounts", "UpstreamProvider")
    ProviderRequestUpstreamProvider = apps.get_model(
        "accounts", "ProviderRequestUpstreamProvider"
    )

    connection = schema_editor.connection

    # Hostingprovider self-referential M2M:
    # auto table name is accounts_hostingprovider_upstream_providers
    # columns: from_hostingprovider_id, to_hostingprovider_id
    table_names = connection.introspection.table_names()
    cursor = connection.cursor()
    try:
        if "accounts_hostingprovider_upstream_providers" in table_names:
            cursor.execute(
                "SELECT from_hostingprovider_id, to_hostingprovider_id "
                "FROM accounts_hostingprovider_upstream_providers"
            )
            for parent_id, upstream_id in cursor.fetchall():
                UpstreamProvider.objects.get_or_create(
                    parent_id=parent_id,
                    upstream_id=upstream_id,
                    defaults={"is_public": True},
                )

        # ProviderRequest -> Hostingprovider M2M:
        # auto table name is accounts_providerrequest_upstream_providers
        # columns: providerrequest_id, hostingprovider_id
        if "accounts_providerrequest_upstream_providers" in table_names:
            cursor.execute(
                "SELECT providerrequest_id, hostingprovider_id "
                "FROM accounts_providerrequest_upstream_providers"
            )
            for request_id, upstream_id in cursor.fetchall():
                ProviderRequestUpstreamProvider.objects.get_or_create(
                    request_id=request_id,
                    upstream_id=upstream_id,
                    defaults={"is_public": True},
                )
    finally:
        cursor.close()


def remove_upstream_connections(apps, schema_editor):
    """
    Reverse: clear the new through tables.
    """
    UpstreamProvider = apps.get_model("accounts", "UpstreamProvider")
    ProviderRequestUpstreamProvider = apps.get_model(
        "accounts", "ProviderRequestUpstreamProvider"
    )
    UpstreamProvider.objects.all().delete()
    ProviderRequestUpstreamProvider.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0109_create_claim_percentage_flag"),
    ]

    operations = [
        # 1. Create the new through model tables in the database.
        migrations.CreateModel(
            name="ProviderRequestUpstreamProvider",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="created",
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="modified",
                    ),
                ),
                (
                    "is_public",
                    models.BooleanField(
                        default=True,
                        help_text=(
                            "If unchecked, this upstream connection will not be "
                            "shown in the public directory."
                        ),
                        verbose_name="Visible publicly",
                    ),
                ),
                (
                    "request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="upstream_connections",
                        to="accounts.providerrequest",
                    ),
                ),
                (
                    "upstream",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="accounts.hostingprovider",
                    ),
                ),
            ],
            options={
                "unique_together": {("request", "upstream")},
            },
        ),
        migrations.CreateModel(
            name="UpstreamProvider",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="created",
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="modified",
                    ),
                ),
                (
                    "is_public",
                    models.BooleanField(
                        default=True,
                        help_text=(
                            "If unchecked, this upstream connection will not be "
                            "shown in the public directory."
                        ),
                        verbose_name="Visible publicly",
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="upstream_connections",
                        to="accounts.hostingprovider",
                    ),
                ),
                (
                    "upstream",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="downstream_connections",
                        to="accounts.hostingprovider",
                    ),
                ),
            ],
            options={
                "unique_together": {("parent", "upstream")},
            },
        ),
        # 2. Copy existing M2M rows into the new through tables.
        migrations.RunPython(
            copy_existing_upstream_connections,
            reverse_code=remove_upstream_connections,
        ),
        # 3. Switch the M2M fields to use the new through models in Django's
        #    state only. The database is untouched: the old auto-generated
        #    M2M table remains (now unused), and the through tables already
        #    exist from step 1. We use RemoveField + AddField wrapped in
        #    SeparateDatabaseAndState so Django doesn't try to ALTER the
        #    M2M field (which Django doesn't support).
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name="providerrequest",
                    name="upstream_providers",
                ),
                migrations.AddField(
                    model_name="providerrequest",
                    name="upstream_providers",
                    field=models.ManyToManyField(
                        blank=True,
                        help_text=(
                            "Active verified providers this request relies on "
                            "for its green status."
                        ),
                        related_name="downstream_provider_requests",
                        through="accounts.ProviderRequestUpstreamProvider",
                        to="accounts.hostingprovider",
                        verbose_name="Upstream providers",
                    ),
                ),
                migrations.RemoveField(
                    model_name="hostingprovider",
                    name="upstream_providers",
                ),
                migrations.AddField(
                    model_name="hostingprovider",
                    name="upstream_providers",
                    field=models.ManyToManyField(
                        blank=True,
                        help_text=(
                            "Other active verified providers this provider relies "
                            "on for its green status."
                        ),
                        related_name="downstream_providers",
                        through="accounts.UpstreamProvider",
                        to="accounts.hostingprovider",
                        verbose_name="Upstream providers",
                    ),
                ),
            ],
            database_operations=[],
        ),
        migrations.RunPython(
            populate_group_permissions,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
