# Generated manually on 2026-05-27

from django.db import migrations


def create_upstream_providers_flag(apps, schema_editor):
    """Create the upstream_providers waffle flag, defaulting to off for everyone."""
    Flag = apps.get_model("waffle", "Flag")
    Flag.objects.get_or_create(
        name="upstream_providers",
        defaults={
            "everyone": False,
            "superusers": False,
            "staff": False,
            "authenticated": False,
            "note": (
                "Controls visibility of the upstream providers feature in the wizard, "
                "portal, and public directory."
            ),
        },
    )


def remove_upstream_providers_flag(apps, schema_editor):
    Flag = apps.get_model("waffle", "Flag")
    Flag.objects.filter(name="upstream_providers").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0093_hostingprovider_linked_providers_and_more"),
        ("accounts", "0095_apikeyprivilegelevel_apikey_privilege_level"),
        ("waffle", "0004_update_everyone_nullbooleanfield"),
    ]

    operations = [
        migrations.RunPython(
            create_upstream_providers_flag,
            reverse_code=remove_upstream_providers_flag,
        ),
    ]
