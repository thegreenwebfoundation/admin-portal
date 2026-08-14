"""Create the link_disclosures_to_regions waffle flag, defaulting to off."""

from django.db import migrations


def create_link_disclosures_to_regions_flag(apps, schema_editor):
    """Create the link_disclosures_to_regions waffle flag."""
    Flag = apps.get_model("waffle", "Flag")
    Flag.objects.get_or_create(
        name="link_disclosures_to_regions",
        defaults={
            "everyone": False,
            "superusers": False,
            "staff": False,
            "authenticated": False,
            "note": (
                "Controls visibility of the region scope / locations fields on the "
                "wizard evidence step. When off, the fields are popped from the form "
                "and evidence is automatically given an 'all regions' scope. The admin "
                "always shows the locations field."
            ),
        },
    )


def remove_link_disclosures_to_regions_flag(apps, schema_editor):
    Flag = apps.get_model("waffle", "Flag")
    Flag.objects.filter(name="link_disclosures_to_regions").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0115_backfill_hostingproviderlocation"),
        ("waffle", "0004_update_everyone_nullbooleanfield"),
    ]

    operations = [
        migrations.RunPython(
            create_link_disclosures_to_regions_flag,
            reverse_code=remove_link_disclosures_to_regions_flag,
        ),
    ]
