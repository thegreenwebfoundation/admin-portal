# Generated manually on 2026-08-14

from django.db import migrations


def create_upstream_providers_directory_flag(apps, schema_editor):
    """Create the upstream_providers_directory waffle flag, defaulting to off."""
    Flag = apps.get_model("waffle", "Flag")
    Flag.objects.get_or_create(
        name="upstream_providers_directory",
        defaults={
            "everyone": False,
            "superusers": False,
            "staff": False,
            "authenticated": False,
            "note": (
                "Controls whether upstream provider relationships are displayed "
                "in the public directory. When off, the 'Relies on' section is "
                "hidden even if providers have public upstream connections."
            ),
        },
    )


def remove_upstream_providers_directory_flag(apps, schema_editor):
    Flag = apps.get_model("waffle", "Flag")
    Flag.objects.filter(name="upstream_providers_directory").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0112_create_private_upstream_linking_flag"),
        ("waffle", "0004_update_everyone_nullbooleanfield"),
    ]

    operations = [
        migrations.RunPython(
            create_upstream_providers_directory_flag,
            reverse_code=remove_upstream_providers_directory_flag,
        ),
    ]
