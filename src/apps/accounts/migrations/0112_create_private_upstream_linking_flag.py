# Generated manually on 2026-08-13

from django.db import migrations


def create_private_upstream_linking_flag(apps, schema_editor):
    """Create the private_upstream_linking waffle flag, defaulting to off for everyone."""
    Flag = apps.get_model("waffle", "Flag")
    Flag.objects.get_or_create(
        name="private_upstream_linking",
        defaults={
            "everyone": False,
            "superusers": False,
            "staff": False,
            "authenticated": False,
            "note": (
                "Controls visibility of the per-provider 'show in public directory' "
                "checkboxes in the verification wizard and the privacy labels in the "
                "provider portal request detail."
            ),
        },
    )


def remove_private_upstream_linking_flag(apps, schema_editor):
    Flag = apps.get_model("waffle", "Flag")
    Flag.objects.filter(name="private_upstream_linking").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0111_upstream_provider_verbose_name"),
        ("waffle", "0004_update_everyone_nullbooleanfield"),
    ]

    operations = [
        migrations.RunPython(
            create_private_upstream_linking_flag,
            reverse_code=remove_private_upstream_linking_flag,
        ),
    ]
