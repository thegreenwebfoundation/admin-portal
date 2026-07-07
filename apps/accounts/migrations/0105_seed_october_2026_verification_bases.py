# Generated manually on 2026-06-28

from django.db import migrations
from django.utils.text import slugify

RESELLER_SLUG = (
    "we-resell-or-actively-use-a-provider-that-is-already-in-the-green-web-dataset"
)
RESELLING_EVIDENCE_LINK = (
    "https://www.thegreenwebfoundation.org/what-we-accept-as-evidence-"
    "of-green-power/#reselling"
)

OCTOBER_2026_BASES = [
    {
        "slug": "self-generation",
        "name": "Self generation",
        "description": "You generate your own fossil-free energy.",
        "required_evidence_link": (
            "https://www.thegreenwebfoundation.org/verification/disclosures/"
            "self-generation"
        ),
    },
    {
        "slug": "direct-procurement",
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
        "slug": "green-tariffs",
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
        "slug": "unbundled-certificates",
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
        "slug": "passive-procurement",
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
    {
        "slug": "we-use-a-non-verified-provider",
        "name": "We use a provider that is not verified",
        "description": (
            "You rely on an upstream provider for green services, but that "
            "provider is not verified in the Green Web Dataset."
        ),
        "required_evidence_link": RESELLING_EVIDENCE_LINK,
    },
    {
        "slug": RESELLER_SLUG,
        "name": "We resell/use an existing verified green provider",
        "description": (
            "You rely on an upstream provider that is already verified in the "
            "Green Web Dataset."
        ),
        "required_evidence_link": RESELLING_EVIDENCE_LINK,
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

    The resell basis was originally created by migration 0067 as a June 2026
    criterion; here we promote it to the October 2026 set and update its name
    and evidence link to match the new upstream-provider split.
    """
    VerificationBasis = apps.get_model("accounts", "VerificationBasis")
    for base in OCTOBER_2026_BASES:
        VerificationBasis.objects.update_or_create(
            slug=base["slug"],
            defaults={
                "name": base["name"],
                "description": base["description"],
                "required_evidence_link": base["required_evidence_link"],
                "version": "2026-10",
            },
        )


def remove_october_2026_bases(apps, schema_editor):
    """
    Reverse: delete bases introduced by this migration and revert the resell
    basis to its June 2026 name/link so it remains a valid legacy criterion.
    """
    VerificationBasis = apps.get_model("accounts", "VerificationBasis")

    # Revert the resell basis (existed before this migration).
    VerificationBasis.objects.filter(slug=RESELLER_SLUG).update(
        version="2026-06",
        name="We resell or actively use a provider that is already in the Green Web Dataset",
        required_evidence_link=None,
    )

    # The remaining five bases were introduced by this migration; remove them.
    remaining_slugs = [
        base["slug"]
        for base in OCTOBER_2026_BASES
        if base["slug"] != RESELLER_SLUG
        and base["slug"] != "we-use-a-non-verified-provider"
    ]
    VerificationBasis.objects.filter(slug__in=remaining_slugs).delete()


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
