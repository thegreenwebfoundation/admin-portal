# ADR 4: Disclosure Claims — Tracking What a Disclosure Supports

## Status

Draft

## Context

A hosting provider earns its green status by submitting **disclosures** —
supporting documents (an energy certificate, an annual report, a web page)
that evidence its green energy claims. Until now, a disclosure was a fairly
opaque artifact: it had a title, a type, a link/attachment, and a
`verification_basis` chosen *at the organisation level*. Nothing in the data
model captured, per disclosure, **which specific claim or claims that
disclosure supports**.

The organisation-level verification bases already recorded *why* a provider
considers itself green (e.g. "We run on 100% green energy from our own
infrastructure", "We purchase quality carbon offsets"). But there was no way to
say **"this particular energy certificate supports the 100%-renewables
generation claim, whereas this other document is the third-party assurance of
that claim"**.

This matters for a few reasons:

1. **Trustworthiness.** Users of the directory want to see not just *that* a
   provider holds disclosures, but *what each disclosure actually claims*. A
   certificate that supports one basis is not interchangeable with a document
   that supports another.
2. **Reviewability.** Staff reviewing a provider request need to be able to
   tell, at a glance, which claims a given piece of evidence backs — and to
   correct mistakes during review.
3. **Machine-readability.** The carbon.txt model already exposes disclosures
   with a `doc_type` and title. Being able to tag each disclosure with the
   claims it supports gives us a structured, queryable relationship that free
   text cannot.

### Requirements

1. A **reference model** of possible claims a disclosure can support must
   exist, so the same claim is shared across the request and the live provider.
2. Each disclosure must be able to support **multiple claims**, and any subset
   of the available claims should be selectable.
3. The provider registration wizard must let submitters **pick, per disclosure,
   which claims it supports**.
4. The approval flow must **carry disclosure-claim links** from the draft
   request to the live provider record.
5. The Django admin must let staff **edit the claims a disclosure supports**,
   together with the rest of the disclosure, so mistakes found during review
   can be corrected in one place.
6. The feature must be **gated behind a waffle flag** (`disclosure_claims`) so
   it can be rolled out incrementally and disabled if problems arise.
7. Claims offered in the wizard must track the **organisation-level
   verification bases** the submitter selected in Step 3, so the per-disclosure
   picker reflects the basis a provider is actually claiming.

### Options considered

#### Option A — A free-text `claims` field on each disclosure

Let submitters type a comma-separated description of what a disclosure
supports (e.g. "generation", "offsets").

**Rejected.** Unstructured text cannot be queried, cannot be consistently
linked across the draft/live boundary, is prone to typos and inconsistency, and
does not give staff or users a stable, filterable vocabulary. It would not
enable "show me all disclosures that support the 100%-renewables generation
claim".

#### Option B — ManyToMany from disclosures directly to `VerificationBasis`

Reuse the existing `VerificationBasis` tag as the claim, adding a
`ManyToManyField` on `ProviderRequestEvidence` and
`HostingProviderSupportingDocument`.

**Rejected.** `VerificationBasis` is an organisation-level tag describing *why*
a provider is green, not a per-disclosure statement of *what a specific
document supports*. It also lacks the "always available" claims (e.g. "this
contains a third-party independent assurance statement" and "I'd like help
confirming this") that only make sense at the disclosure granularity. Using it
directly would conflate two distinct concepts and make the disclosure-level
distinctions impossible. Furthermore, an implicit through table would prevent
adding per-link metadata or a human-readable `verbose_name` in the admin.

#### Option C — A dedicated `DisclosureClaim` reference model with explicit through models _(chosen)_

Introduce a `DisclosureClaim` reference model carrying a `slug`, `label`,
`category`, an optional link back to a `VerificationBasis`, and a version.
Link disclosures to claims with two explicit through models —
`ProviderRequestEvidenceClaim` (draft side) and
`HostingProviderSupportingDocumentClaim` (live side). Carry the links across
during `approve()` (the claims reference data is shared, so the same FK is
valid on both sides).

**Selected.** This gives a stable, queryable vocabulary of claims; a clean
divide between draft and live linkage; an explicit through model with
`unique_together`; and a shared reference dataset that survives approval
without remapping.

## Decision

We will introduce a **`DisclosureClaim` reference model** and link disclosures
to claims through **two explicit through models** (one draft, one live), gated
behind the `disclosure_claims` waffle flag. Staff can edit the claims a
disclosure supports from a dedicated per-disclosure admin page.

### 1. The reference model

`DisclosureClaim` is **shared reference data** — it is *not* part of the
draft/live split. A single claim instance is referenced by both the draft
through model and the live through model, so no remapping is required on
approval.

```python
# src/apps/accounts/models/hosting/provider.py

class DisclosureClaim(models.Model):
    """
    A claim that a disclosure can be said to support.

    Categories:
    - ``ORGANISATION_BASIS``: a per-disclosure view of a VerificationBasis
      chosen at the organisation level (Step 3). Linked via the ``basis`` FK.
    - ``THIRD_PARTY_ASSURANCE``: the always-on "this disclosure contains a
      third-party independent assurance statement" option.
    - ``NEEDS_HELP``: the always-on "I'd like help confirming this" fallback.
    """

    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    label = models.CharField(max_length=255)
    category = models.CharField(
        max_length=64, choices=DisclosureClaimType.choices
    )
    basis = models.ForeignKey(
        VerificationBasis,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="disclosure_claims",
    )
    version = models.CharField(
        max_length=128,
        choices=VerificationBasisVersion.choices,
        null=True,
        blank=True,
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "disclosure claim"
        verbose_name_plural = "disclosure claims"
        ordering = ("sort_order", "id")
```

The `category` values are defined in the shared `DisclosureClaimType` choices:
- `organisation_basis` — created per `VerificationBasis` (one per basis, per
  version), carrying a `basis` FK and a `version`.
- `third_party_assurance` — the always-on assurance claim, version-agnostic.
- `needs_help` — the always-on "I'd like help confirming this" fallback,
  version-agnostic.

`ORGANISATION_BASIS` claims are seeded per active verification-basis version so
the label tracks the chosen basis. `THIRD_PARTY_ASSURANCE` and `NEEDS_HELP` are
seeded once. When staff add a new `VerificationBasis` via the admin, a
corresponding `DisclosureClaim` is created lazily by the wizard when building
the per-disclosure choices.

### 2. The through models

Both disclosures gain a `claims` many-to-many relationship backed by an
explicit through model:

```python
# src/apps/accounts/models/provider_request.py (draft side)

class ProviderRequestEvidence(models.Model):
    # ...
    claims = models.ManyToManyField(
        DisclosureClaim,
        through="ProviderRequestEvidenceClaim",
        blank=True,
        related_name="evidence_draft",
    )

class ProviderRequestEvidenceClaim(models.Model):
    """Link between a draft disclosure and a DisclosureClaim."""

    evidence = models.ForeignKey(
        ProviderRequestEvidence,
        on_delete=models.CASCADE,
        related_name="claim_links",
    )
    claim = models.ForeignKey(
        DisclosureClaim,
        on_delete=models.CASCADE,
        related_name="evidence_links_draft",
    )

    class Meta:
        unique_together = ("evidence", "claim")
        verbose_name = "disclosure claim"
        verbose_name_plural = "disclosure claims"
```

```python
# src/apps/accounts/models/hosting/provider.py (live side)

class HostingProviderSupportingDocument(models.Model):
    # ...
    claims = models.ManyToManyField(
        DisclosureClaim,
        through="HostingProviderSupportingDocumentClaim",
        blank=True,
        related_name="supporting_documents",
    )

class HostingProviderSupportingDocumentClaim(models.Model):
    """Link between a live disclosure and a DisclosureClaim."""

    document = models.ForeignKey(
        "HostingProviderSupportingDocument",
        on_delete=models.CASCADE,
        related_name="claim_links",
    )
    claim = models.ForeignKey(
        DisclosureClaim,
        on_delete=models.CASCADE,
        related_name="document_links_live",
    )

    class Meta:
        unique_together = ("document", "claim")
        verbose_name = "disclosure claim"
        verbose_name_plural = "disclosure claims"
```

The `unique_together` constraint prevents a disclosure claiming the same
`DisclosureClaim` twice.

### 3. A human-readable `claims_display`

Both disclosure models expose a `claims_display` property that renders the
linked claims as a comma-separated list for the admin and the provider portal:

```python
@property
def claims_display(self) -> str:
    """Return a human-readable, comma-separated list of claim labels."""
    claims = self.claims.all()
    if not claims:
        return "None"
    return ", ".join(c.label for c in claims)
```

### 4. The wizard: picking claims per disclosure

The organisation-level bases the submitter chose in Step 3
(`BasisForVerification`) determine which organisation-basis claims are offered
on each disclosure row in the evidence step. The wizard builds the choices with
`_get_disclosure_claim_choices()`, which returns a list of `(claim_slug, label)`
tuples:

- one `basis--<slug>` claim per selected verification basis,
- plus the two always-on claims (`third-party-independent-assurance`,
  `i-would-like-help-confirming-this`).

`DisclosureClaim` rows are **created lazily** (in a single `bulk_create`) for
any selected basis that does not yet have a claim, so the picker stays in sync
with newly admin-created bases. The result is memoised for the request to avoid
re-seeding or re-querying across the several calls per render.

The `CredentialForm` (used inside the evidence formset) gains a
`claim_choices` multi-select field (`CheckboxSelectMultiple`) whose choices are
injected by the wizard:

```python
# src/apps/accounts/forms/provider_request_wizard.py

claim_choices = forms.MultipleChoiceField(
    choices=[],
    required=False,
    widget=forms.CheckboxSelectMultiple,
)
```

When the wizard submits the evidence step, `done()` resolves the selected slugs
and creates the through-model rows:

```python
for claim_slug in form.cleaned_data.get("claim_choices", []):
    ProviderRequestEvidenceClaim.objects.create(
        evidence=evidence,
        claim=DisclosureClaim.objects.get(slug=claim_slug),
    )
```

### 5. The approval flow: carrying claims to live data

`DisclosureClaim` is **shared reference data**, so unlike locations there is no
draft/live remapping on approval — the same `claim` FK is valid on both sides.
When `ProviderRequest.approve()` creates a live supporting document for each
draft disclosure it uses `get_or_create` so a re-approval does not duplicate
rows:

```python
# src/apps/accounts/models/provider_request.py (approve method)

for claim in evidence.claims.all():
    HostingProviderSupportingDocumentClaim.objects.get_or_create(
        document=supporting_doc,
        claim=claim,
    )
```

### 6. The admin: editing a disclosure's claims

Because the claims relation uses an explicit through model, Django's admin
inline formsets cannot render it as an editable field. The earlier
`edit_disclosure_claims` bulk page was superseded by a **per-disclosure edit
page** — each disclosure listed in the hosting-provider and provider-request
admin change pages links (via an `edit_link` in the relevant inline) to a
dedicated `edit_disclosure` view.

That view uses a per-model `ModelForm` — `ProviderRequestEvidenceEditForm`
(draft) or `HostingProviderSupportingDocumentEditForm` (live) — built on a
shared `DisclosureEditFormMixin`. The mixin renders `locations` and `claims` as
`CheckboxSelectMultiple` fields, with claims **grouped by version** so staff can
see at a glance which claims belong to which verification regime. The view then
persists the selected claims through the through model (clear existing links,
recreate from the selection), alongside the disclosure's other fields:

```python
# src/apps/accounts/forms/admin.py (shared via DisclosureEditFormMixin)

self.fields["claims"] = forms.MultipleChoiceField(
    choices=self._build_claim_choices(claims_qs),
    required=False,
    widget=forms.CheckboxSelectMultiple,
    ...
)
```

```python
# src/apps/accounts/admin/provider_request.py (edit_disclosure view)

updated_evidence = form.save(commit=False)
updated_evidence.save()

selected_claim_pks = form.cleaned_data.get("claims", [])
ProviderRequestEvidenceClaim.objects.filter(evidence=updated_evidence).delete()
for pk in selected_claim_pks:
    ProviderRequestEvidenceClaim.objects.create(
        evidence=updated_evidence, claim_id=pk,
    )
```

### 7. The waffle flag

The `disclosure_claims` flag gates the per-disclosure `claim_choices` field in
the wizard's evidence step. When the flag is off:

- `claim_choices` is popped from `CredentialForm` in `__init__`.
- `clean()` defaults `claim_choices` to `[]`, so `done()` creates no through
  rows.
- The claim picker UI in the evidence template is not rendered.

This matches the gating approach used for region scoping (see ADR 3) and lets
the feature be rolled out and rolled back at runtime without migrations.

## Why this is useful

1. **Disclosures become evidence of something specific.** Instead of an opaque
   document, a disclosure is now explicitly linked to the claim(s) it supports
   — "this energy certificate backs the 100%-renewables generation claim; this
   other document is the third-party assurance of it."

2. **It is queryable and structured.** Because claims are stored as rows in a
   shared reference model with explicit through models, we can answer "which
   disclosures support claim X?" and "which claims does disclosure Y back?"
   without parsing free text.

3. **It is verifiable by staff.** The admin shows a `claims_display` readout on
   every disclosure and, crucially, lets staff edit the claims from a dedicated
   per-disclosure page discovered directly from the change view — so mistakes
   found during review are corrected in one place.

4. **It survives approval cleanly.** `DisclosureClaim` is shared reference data,
   so the same foreign key is valid on both the draft and live sides. The
   `approve()` method carries claim links across with `get_or_create` and no
   remapping logic, avoiding the index-based fragility of the location mapping
   (see ADR 3).

5. **It tracks the provider's actual basis.** The wizard derives the offered
   claims from the verification bases the provider selected, and lazily creates
   claims for newly added bases, so the per-disclosure vocabulary stays aligned
   with the organisation-level basis.

## Consequences

### Positive

1. **A shared, stable claim vocabulary.** `DisclosureClaim` provides a single
   source of truth for the claims a disclosure can support, reused by both the
   draft and live graphs and by the admin.

2. **Correct per-disclosure granularity.** The `third_party_assurance` and
   `needs_help` always-on claims could only ever be disclosure-level concepts;
   a dedicated model makes them first-class rather than bolted onto the
   organisation level.

3. **Clean admin editing surface.** The per-disclosure `edit_disclosure` page
   lets staff change a disclosure's details, region scope, and claims in one
   visit, discovered via a link on each disclosure in the change view.

4. **The draft/live split stays tidy.** Through models are explicit with
   `unique_together`, and because the claim reference is shared there is no
   remapping burden in `approve()`.

5. **The feature is reversible.** The `disclosure_claims` waffle flag can be
   toggled off at runtime; when off, the wizard simply creates no through rows
   and behaves like the pre-feature version.

### Negative

1. **A third parallel through-model pair.** Like the region-linking feature
   (ADR 3), disclosure-claim linking adds `ProviderRequestEvidenceClaim` and
   `HostingProviderSupportingDocumentClaim` — two near-identical models. This
   is consistent with the existing draft/live pattern, but it is more code to
   maintain and the `approve()` method must remember to copy the claim links.

2. **Claims require a bounded vocabulary.** Users can only select from
   pre-seeded `DisclosureClaim` rows. If a provider needs to express a claim
   that has no matching `DisclosureClaim`, a new reference row must be created
   first. This is the intended trade-off for a queryable, consistent model, but
   it is less flexible than free text.

3. **The admin form must manually rebuild through-model rows.** Because the
   M2M uses an explicit through model, the `edit_disclosure` view clears and
   recreates the `ProviderRequestEvidenceClaim` / `HostingProviderSupportingDocumentClaim`
   rows on every save rather than going through Django's `save_m2m`. This is
   correct for this small staff-facing surface but bypasses the usual ModelForm
   machinery.

### Risks and mitigations

| Risk | Mitigation |
|------|------------|
| A disclosure accidentally claims support for a basis it does not evidence | The wizard offers claims derived from the provider's own selected bases; staff can correct mistakes via the per-disclosure admin page |
| Newly admin-created bases have no matching claim | `_ensure_disclosure_claims_for_bases` lazily creates them in a single `bulk_create` before building choices |
| Re-approval duplicates claim links | `approve()` uses `get_or_create` for `HostingProviderSupportingDocumentClaim` |
| Waffle flag toggled off loses data | Toggling off only stops the wizard creating new rows; existing through-model rows are left intact |
| Claims vocabulary drifts from verification bases | The `version` field on `DisclosureClaim` separates claims by regime, and lazy seeding keeps them in sync |

## Verification

After implementing this change, the following was verified:

| Check | Result |
|-------|--------|
| `DisclosureClaim` lazy creation (per basis, per version, always-on) | Reference rows created on demand; seeded for both versions |
| `ProviderRequestEvidenceClaim` / `HostingProviderSupportingDocumentClaim` | Through-model creation, unique constraint, cascade deletes pass |
| `claims_display` property (both draft and live) | Returns "None" or a comma-separated claim list |
| `_get_disclosure_claim_choices()` | Returns selected bases (as `basis--<slug>`) plus always-on claims; memoised and lazy-seeded |
| `TestWizardSubmissionWithClaims` | `claim_choices` submission creates through rows; flag-off creates no rows |
| `TestApprovalFlow` | `approve()` carries claim links to live through-model rows via `get_or_create` |
| `TestAdminEditDisclosureView` | Per-disclosure edit page loads and persists claims for both hosting provider and provider request |

## References

- [Django many-to-many relationships with through models](https://docs.djangoproject.com/en/dev/topics/db/models/#extra-fields-on-many-to-many-relationships)
- [Django admin inlines and M2M with through models](https://docs.djangoproject.com/en/dev/topics/db/models/#django.db.models.ManyToManyField.through) — known limitation: admin inline formsets omit M2M fields with explicit through models, motivating the per-disclosure edit page
- [django-waffle](https://waffle.readthedocs.io/) — feature flags for Django
- ADR 3: Location Support — Linking Disclosures to Regions — the parallel draft/live through-model pattern this feature extends, and the shared-feature-gating approach
- ADR 2: TomSelect for Autocomplete Multi-Selects — the disclosure-claims picker styling/behaviour for multi-select lists
