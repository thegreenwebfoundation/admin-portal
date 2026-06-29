# Generated manually on 2026-06-28

from django.db import migrations


def create_verification_basis_v2_flag(apps, schema_editor):
    """
    Create the verification_basis_v2 waffle flag.

    ``everyone=None`` (rather than ``False``) is required so that waffle's
    ``Flag.is_active`` falls through from the ``everyone`` short-circuit to
    the per-user / per-group checks. With ``everyone=False``, waffle returns
    False immediately and never consults the ``users`` / ``groups`` M2M
    relations, which would make the planned per-user rollout a no-op.
    Superusers/staff/authenticated are also left unset for the same reason.
    """
    Flag = apps.get_model("waffle", "Flag")
    Flag.objects.get_or_create(
        name="verification_basis_v2",
        defaults={
            "everyone": None,
            "superusers": False,
            "staff": False,
            "authenticated": False,
            "note": (
                "Controls visibility of October 2026 verification basis criteria "
                "in request forms. Set everyone=None (default) for per-user/per-group "
                "rollout; flip everyone=True for the global October 2026 switchover."
            ),
        },
    )


def remove_verification_basis_v2_flag(apps, schema_editor):
    Flag = apps.get_model("waffle", "Flag")
    Flag.objects.filter(name="verification_basis_v2").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0103_add_verificationbasis_version_and_description"),
        ("waffle", "0004_update_everyone_nullbooleanfield"),
    ]

    operations = [
        migrations.RunPython(
            create_verification_basis_v2_flag,
            reverse_code=remove_verification_basis_v2_flag,
        ),
    ]
