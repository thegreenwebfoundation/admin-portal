"""Seed DisclosureClaim rows from VerificationBasis + two always-on claims."""

from django.db import migrations


# The two version-agnostic, always-on claims shown on every disclosure row
ALWAYS_ON_CLAIMS = [
    {
        "slug": "third-party-independent-assurance",
        "label": (
            "This contains a third-party independent assurance statement."
        ),
        "category": "third_party_assurance",
    },
    {
        "slug": "i-would-like-help-confirming-this",
        "label": "I'm not sure - I'd like help confirming this",
        "category": "needs_help",
    },
]


def seed_disclosure_claims(apps, schema_editor):
    """
    Seed one ``DisclosureClaim`` per ``VerificationBasis`` (category
    ``organisation_basis``), plus the two version-agnostic always-on claims.

    Organisation-basis claims use the slug ``basis--{basis.slug}`` so they
    can be looked up deterministically by the wizard, and track the basis's
    ``version``. The two always-on claims are seeded once and have no
    ``version`` (version-agnostic).

    Idempotent: uses ``get_or_create`` keyed on ``slug``.
    """
    VerificationBasis = apps.get_model("accounts", "VerificationBasis")
    DisclosureClaim = apps.get_model("accounts", "DisclosureClaim")

    # Organisation-basis claims: one per VerificationBasis, across both
    # June 2026 and October 2026 versions.
    for basis in VerificationBasis.objects.all():
        DisclosureClaim.objects.get_or_create(
            slug=f"basis--{basis.slug}",
            defaults={
                "label": basis.name,
                "category": "organisation_basis",
                "basis": basis,
                "version": basis.version,
            },
        )

    # The two always-on claims.
    for claim in ALWAYS_ON_CLAIMS:
        DisclosureClaim.objects.get_or_create(
            slug=claim["slug"],
            defaults={
                "label": claim["label"],
                "category": claim["category"],
            },
        )


def remove_disclosure_claims(apps, schema_editor):
    DisclosureClaim = apps.get_model("accounts", "DisclosureClaim")
    DisclosureClaim.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0117_disclosureclaim_and_through_models"),
    ]

    operations = [
        migrations.RunPython(
            seed_disclosure_claims,
            reverse_code=remove_disclosure_claims,
        ),
    ]
