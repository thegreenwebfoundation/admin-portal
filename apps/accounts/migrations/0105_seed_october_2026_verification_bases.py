# Generated manually on 2026-06-28

from django.db import migrations
from django.utils.text import slugify


OCTOBER_2026_BASES = [
    {
        "name": "Self generation",
        "description": "You generate your own fossil-free energy.",
        "required_evidence_link": (
            "https://www.thegreenwebfoundation.org/verification/disclosures/"
            "self-generation"
        ),
    },
    {
        "name": "Direct procurement",
        "description": (
            "You buy directly from a fossil-free energy project via a dedicated "
            "power purchase agreement."
        ),
        "required_evidence_link": (
            "https://www.thegreenwebfoundation.org/verification/disclosures/"
            "direct-procurement"
        ),
    },
    {
        "name": "Green tariffs",
        "description": (
            "You actively procure a fossil-free energy tariff via electricity "
            "suppliers."
        ),
        "required_evidence_link": (
            "https://www.thegreenwebfoundation.org/verification/disclosures/"
            "green-tariff"
        ),
    },
    {
        "name": "Unbundled certificates",
        "description": (
            "You buy certificates of fossil-free generation separate from the "
            "power you buy, when you or your supplier can't rely on "
            "self-generation, direct procurement, or a green tariff."
        ),
        "required_evidence_link": (
            "https://www.thegreenwebfoundation.org/verification/disclosures/"
            "unbundled-certificates"
        ),
    },
    {
        "name": "Passive procurement",
        "description": (
            "You operate in a place where certificates for fossil-free "
            "generation are by default bundled with the power you buy, and not "
            "sold on."
        ),
        "required_evidence_link": (
            "https://www.thegreenwebfoundation.org/verification/disclosures/"
            "passive-procurement"
        ),
    },
]


def seed_october_2026_bases(apps, schema_editor):
    """
    Create the October 2026 verification bases.

    ``name`` holds the short category title shown in the form (via the
    ``label`` property), ``description`` holds the full descriptive sentence
    for internal admin context, and ``required_evidence_link`` points at the
    public documentation page for each criterion (surfaced in the form as a
    "see required evidence" hyperlink appended to the label). Seeded with
    ``version='2026-10'``; visibility is gated by the
    ``verification_basis_v2`` waffle flag.
    """
    VerificationBasis = apps.get_model("accounts", "VerificationBasis")
    for base in OCTOBER_2026_BASES:
        VerificationBasis.objects.get_or_create(
            slug=slugify(base["name"]),
            defaults={
                "name": base["name"],
                "description": base["description"],
                "required_evidence_link": base["required_evidence_link"],
                "version": "2026-10",
            },
        )


def remove_october_2026_bases(apps, schema_editor):
    VerificationBasis = apps.get_model("accounts", "VerificationBasis")
    slugs = [slugify(b["name"]) for b in OCTOBER_2026_BASES]
    VerificationBasis.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0104_create_verification_basis_v2_flag"),
    ]

    operations = [
        migrations.RunPython(
            seed_october_2026_bases,
            reverse_code=remove_october_2026_bases,
        ),
    ]
