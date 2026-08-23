from django.db import migrations

# The Hostingprovider model sets ``db_table = "hostingproviders"``, so the
# auto-generated M2M through table for its self-referential
# ``upstream_providers`` field is named ``hostingproviders_upstream_providers``
# (after the db_table), NOT ``accounts_hostingprovider_upstream_providers``.
#
# Migration 0110 only looked for the latter name, so on databases where the
# M2M was created after the model already had a db_table it found no rows and
# copied nothing into the new ``accounts.UpstreamProvider`` through model. This
# backfills that gap so existing upstream connections are no longer lost.


def backfill_hostingprovider_upstream_providers(apps, schema_editor):
    UpstreamProvider = apps.get_model("accounts", "UpstreamProvider")

    connection = schema_editor.connection
    table_names = connection.introspection.table_names()

    candidates = [
        name
        for name in (
            "hostingproviders_upstream_providers",
            "accounts_hostingprovider_upstream_providers",
        )
        if name in table_names
    ]

    if not candidates:
        return

    cursor = connection.cursor()
    try:
        # Prefer the table that actually has data, falling back to the first
        # candidate when both exist.
        source = candidates[0]
        if len(candidates) > 1:
            cursor.execute(
                f"SELECT COUNT(*) FROM `{candidates[0]}`"
            )
            if cursor.fetchone()[0] == 0:
                source = candidates[1]

        cursor.execute(
            f"SELECT from_hostingprovider_id, to_hostingprovider_id "
            f"FROM `{source}`"
        )
        for parent_id, upstream_id in cursor.fetchall():
            UpstreamProvider.objects.get_or_create(
                parent_id=parent_id,
                upstream_id=upstream_id,
                defaults={"is_public": True},
            )
    finally:
        cursor.close()


def remove_backfilled_upstream_providers(apps, schema_editor):
    UpstreamProvider = apps.get_model("accounts", "UpstreamProvider")
    UpstreamProvider.objects.filter(is_public=True).all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0119_create_disclosure_claims_flag"),
    ]

    operations = [
        migrations.RunPython(
            backfill_hostingprovider_upstream_providers,
            reverse_code=remove_backfilled_upstream_providers,
        ),
    ]
