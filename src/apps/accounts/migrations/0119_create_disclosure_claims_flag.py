"""Create the disclosure_claims waffle flag, defaulting to off."""

from django.db import migrations


def create_disclosure_claims_flag(apps, schema_editor):
    """Create the disclosure_claims waffle flag."""
    Flag = apps.get_model("waffle", "Flag")
    Flag.objects.get_or_create(
        name="disclosure_claims",
        defaults={
            "everyone": False,
            "superusers": False,
            "staff": False,
            "authenticated": False,
            "note": (
                "Controls visibility of the per-disclosure claim picker on "
                "the wizard evidence step. When off, the claim_choices field "
                "is popped from the form and no ProviderRequestEvidenceClaim "
                "rows are created. The admin always shows claims_display "
                "read-only."
            ),
        },
    )


def remove_disclosure_claims_flag(apps, schema_editor):
    Flag = apps.get_model("waffle", "Flag")
    Flag.objects.filter(name="disclosure_claims").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0118_seed_disclosure_claims"),
        ("waffle", "0004_update_everyone_nullbooleanfield"),
    ]

    operations = [
        migrations.RunPython(
            create_disclosure_claims_flag,
            reverse_code=remove_disclosure_claims_flag,
        ),
    ]
