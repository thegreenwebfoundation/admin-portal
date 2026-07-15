# Generated manually on 2026-07-15

from django.db import migrations


FOSSIL_FREE_2030_NOTE = (
    "Controls the visibility of the fossil-free 2030 target URL field "
    "(public_2030_target_url) in the provider request wizard org-details step "
    "and the provider-portal request detail view. Set everyone=None (default) "
    "for per-user/per-group rollout; flip everyone=True for the global October "
    "2026 switchover."
)

HOURLY_ANNUAL_NOTE = (
    "Controls the visibility of the hourly/annual fossil-free energy matching "
    "fields (fossil_free_energy_matching and, in conjunction with "
    "verification_basis_v2_claimed_percentage, claim_coverage_percentage) on "
    "the evidence step of the provider request wizard. Set everyone=None "
    "(default) for per-user/per-group rollout; flip everyone=True for the "
    "global October 2026 switchover."
)

VERIFICATION_BASIS_V2_UPDATED_NOTE = (
    "Controls visibility of October 2026 verification basis criteria in "
    "request forms (get_active_version, upstream_providers field, legacy slug "
    "conversion, upstream_section_enabled template tag, and the evidence intro "
    "text swap). Note: the fossil-free 2030 target URL and the hourly/annual "
    "disclosure fields now have their own flags "
    "(verification_basis_v2_fossil_free_2030 and "
    "verification_basis_v2_hourly_annual respectively). Set everyone=None "
    "(default) for per-user/per-group rollout; flip everyone=True for the "
    "global October 2026 switchover."
)


def create_split_flags_and_update_note(apps, schema_editor):
    """
    Create the two new split waffle flags and update the note on the
    existing ``verification_basis_v2`` flag to reflect its narrowed scope.

    ``everyone=None`` (rather than ``False``) is required so that waffle's
    ``Flag.is_active`` falls through from the ``everyone`` short-circuit to
    the per-user / per-group checks. With ``everyone=False``, waffle returns
    False immediately and never consults the ``users`` / ``groups`` M2M
    relations, which would make the planned per-user rollout a no-op.
    Superusers/staff/authenticated are also left unset for the same reason.
    """
    Flag = apps.get_model("waffle", "Flag")

    Flag.objects.get_or_create(
        name="verification_basis_v2_fossil_free_2030",
        defaults={
            "everyone": None,
            "superusers": False,
            "staff": False,
            "authenticated": False,
            "note": FOSSIL_FREE_2030_NOTE,
        },
    )

    Flag.objects.get_or_create(
        name="verification_basis_v2_hourly_annual",
        defaults={
            "everyone": None,
            "superusers": False,
            "staff": False,
            "authenticated": False,
            "note": HOURLY_ANNUAL_NOTE,
        },
    )

    Flag.objects.filter(name="verification_basis_v2").update(
        note=VERIFICATION_BASIS_V2_UPDATED_NOTE,
    )


def remove_split_flags_and_restore_note(apps, schema_editor):
    Flag = apps.get_model("waffle", "Flag")
    Flag.objects.filter(
        name__in=[
            "verification_basis_v2_fossil_free_2030",
            "verification_basis_v2_hourly_annual",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0109_create_claim_percentage_flag"),
        ("waffle", "0004_update_everyone_nullbooleanfield"),
    ]

    operations = [
        migrations.RunPython(
            create_split_flags_and_update_note,
            reverse_code=remove_split_flags_and_restore_note,
        ),
    ]
