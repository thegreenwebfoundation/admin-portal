# ADR 3: Location Support — Linking Disclosures to Regions

## Status

Draft

## Context

A hosting provider can operate in multiple regions — a datacentre in
Amsterdam, an office in Singapore, a POP in São Paulo. Until now, the admin
portal modelled a provider's location as a single `country`/`city` pair on the
`Hostingprovider` model. Providers submitted one or more `ProviderRequestLocation`
rows during registration, but these were used only for display — they had no
structural relationship to the provider's **disclosures** (the supporting
documents that evidence green energy claims).

This meant a provider with operations in three regions could not express "this
disclosure covers our Amsterdam and Singapore datacentres, but not São Paulo".
Every disclosure was implicitly global. As the directory grows and providers
operate across more regions, this becomes inadequate — users need to see which
disclosures apply to which regions, and providers need to submit disclosures
scoped to specific locations.

### Requirements

1. A provider must be able to have **multiple locations**, each with a name,
   city, and country.
2. The provider registration wizard must let submitters **scope each
   disclosure** to either "all regions" or a specific subset of their submitted
   locations.
3. The approval flow must **carry disclosure-region links** from the draft
   request to the live provider record.
4. The Django admin must display location and region-scope information
   read-only, so staff can review it without accidentally mutating it.
5. The feature must be **gated behind a waffle flag** (`link_disclosures_to_regions`)
   so it can be rolled out incrementally and disabled if problems arise.
6. Existing providers must be **backfilled** — legacy providers with a flat
   `country`/`city` must get a single `HostingProviderLocation` so the new
   model is consistent across the entire dataset.
7. The flat `Hostingprovider.country`/`.city` fields must remain in sync with
   the primary location, so existing code that reads those fields (directory
   pages, exports, API responses) continues to work unchanged.

### Options considered

#### Option A — ManyToMany on disclosures to locations, no through model

Add a `locations = ManyToManyField("HostingProviderLocation", blank=True)`
directly on `HostingProviderSupportingDocument` and `ProviderRequestEvidence`,
 letting Django create the implicit through table.

**Rejected.** An implicit through table means we cannot add metadata to the
link, query the through model directly, or enforce `unique_together` to
prevent duplicate disclosure-region pairs. We also lose the ability to give the
through model a human-readable `verbose_name` that shows up in the admin
("disclosure regions" rather than "hostingprovidersupportingdocumentlocation").
Explicit through models give us control over cascading, uniqueness, and naming.

#### Option B — A single `region` text field on each disclosure

Add a free-text `region` field to disclosures, letting providers type a
description like "EU-West" or "Amsterdam, Singapore".

**Rejected.** Free text is unstructured — it cannot be linked to the provider's
specific submitted locations, cannot be queried or filtered, and is prone to
typos and inconsistency. This does not enable the directory to show "which
disclosures cover region X" or let users filter by region.

#### Option C — Explicit through models linking disclosures to locations _(chosen)_

Introduce `HostingProviderLocation` as a first-class model, with explicit
through models (`HostingProviderSupportingDocumentLocation` and
`ProviderRequestEvidenceLocation`) linking disclosures to locations. Mirror
this on both the draft side (`ProviderRequest*`) and the live side
(`HostingProvider*`), and carry the links across during `approve()`.

**Selected.** This gives full structural relationships, queryable through
models with uniqueness constraints, clean admin integration, and a clear
separation between draft (request) and live (provider) data.

## Decision

We will introduce **location models** on both the draft and live sides of the
data model, linked by explicit through models, with the feature gated behind
the `link_disclosures_to_regions` waffle flag.

### 1. The model layer

The feature adds four new models across two parallel hierarchies — the **draft**
side (submitted during registration) and the **live** side (created on
approval):

```
Draft side (provider request):              Live side (approved provider):
  ProviderRequestLocation                     HostingProviderLocation
       │                                            │
       │ through                                    │ through
       ▼                                            ▼
  ProviderRequestEvidenceLocation            HostingProviderSupportingDocumentLocation
       │                                            │
       ▼                                            ▼
  ProviderRequestEvidence                    HostingProviderSupportingDocument
```

#### Live models

```python
# src/apps/accounts/models/hosting/provider.py

class HostingProviderLocation(models.Model):
    """
    A live location for a hosting provider. Created from
    ProviderRequestLocation data during approval. An admin can add/remove/edit
    these without mutating the original submitted request data.

    The ``is_primary`` flag marks the location that represents the provider's
    main country/city in the directory. The flat ``Hostingprovider.country``
    and ``.city`` fields are kept in sync with the primary location.
    """

    name = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=255)
    country = CountryField()
    hostingprovider = models.ForeignKey(
        "Hostingprovider",
        on_delete=models.CASCADE,
        related_name="locations",
    )
    is_primary = models.BooleanField(default=False)

    @property
    def display_label(self):
        """Human-friendly label: name, city, country (omits empty parts)."""
        parts = [part for part in (self.name, self.city, self.country.name) if part]
        if parts:
            return ", ".join(parts)
        return f"Location {self.pk}" if self.pk else "Location"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_primary:
            # Ensure only one primary location per provider
            HostingProviderLocation.objects.filter(
                hostingprovider=self.hostingprovider,
                is_primary=True,
            ).exclude(pk=self.pk).update(is_primary=False)
            # Sync the flat fields on the provider
            self.hostingprovider.country = self.country
            self.hostingprovider.city = self.city
            self.hostingprovider.save(update_fields=["country", "city"])


class HostingProviderSupportingDocumentLocation(models.Model):
    """Link between a live disclosure and a live region (location)."""

    document = models.ForeignKey(
        "HostingProviderSupportingDocument",
        on_delete=models.CASCADE,
        related_name="location_links",
    )
    location = models.ForeignKey(
        HostingProviderLocation,
        on_delete=models.CASCADE,
        related_name="document_links",
    )

    class Meta:
        unique_together = ("document", "location")
        verbose_name = "disclosure region"
        verbose_name_plural = "disclosure regions"
```

The `HostingProviderSupportingDocument.locations` M2M field is declared with
the explicit through model:

```python
locations = models.ManyToManyField(
    HostingProviderLocation,
    through="HostingProviderSupportingDocumentLocation",
    blank=True,
    related_name="supporting_documents",
)
```

#### Draft models

The draft side mirrors the live side almost exactly:

```python
# src/apps/accounts/models/provider_request.py

class ProviderRequestLocation(models.Model):
    name = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=255)
    country = CountryField()
    request = models.ForeignKey(ProviderRequest, on_delete=models.CASCADE)

    @property
    def display_label(self) -> str:
        parts = [part for part in (self.name, self.city, self.country.name) if part]
        if parts:
            return ", ".join(parts)
        return f"Location {self.pk}" if self.pk else "Location"


class ProviderRequestEvidenceLocation(models.Model):
    """Link between a draft disclosure and a submitted location."""

    evidence = models.ForeignKey(
        ProviderRequestEvidence,
        on_delete=models.CASCADE,
        related_name="location_links",
    )
    location = models.ForeignKey(
        ProviderRequestLocation,
        on_delete=models.CASCADE,
        related_name="evidence_links",
    )

    class Meta:
        unique_together = ("evidence", "location")
        verbose_name = "evidence region"
        verbose_name_plural = "evidence regions"
```

### 2. The `is_primary` sync behaviour

The `HostingProviderLocation.save()` override does two things when
`is_primary=True`:

1. **Enforces a single primary location** by setting `is_primary=False` on all
   sibling locations of the same provider.
2. **Syncs the flat `country`/`city` fields** on the parent `Hostingprovider`
   to match the primary location.

This means existing code that reads `provider.country` or `provider.city`
(directory pages, exports, API responses) continues to work — it always
reflects the primary location. A backfill migration ensures every existing
provider has at least one location, with the first marked as primary.

### 3. Migrations: schema + backfill + flag

Three migrations are introduced:

**`0114_hostingproviderlocation_and_more.py`** — Creates the four new models
and adds the `locations` M2M fields to both `HostingProviderSupportingDocument`
and `ProviderRequestEvidence` with explicit through models.

**`0115_backfill_hostingproviderlocation.py`** — Data migration that backfills
`HostingProviderLocation` rows for every existing approved provider:

```python
# src/apps/accounts/migrations/0115_backfill_hostingproviderlocation.py

def backfill_hosting_provider_locations(apps, schema_editor):
    Hostingprovider = apps.get_model("accounts", "Hostingprovider")
    ProviderRequest = apps.get_model("accounts", "ProviderRequest")
    ProviderRequestLocation = apps.get_model("accounts", "ProviderRequestLocation")
    HostingProviderLocation = apps.get_model("accounts", "HostingProviderLocation")

    # Idempotency: skip providers that already have locations.
    providers_with_locations = set(
        HostingProviderLocation.objects.values_list("hostingprovider_id", flat=True)
    )

    # Find the latest ProviderRequest for each provider in two queries, not N.
    latest_pr_by_provider = {}
    for pr in (
        ProviderRequest.objects.exclude(provider=None)
        .order_by("provider_id", "-id")
        .values("id", "provider_id")
    ):
        if pr["provider_id"] not in latest_pr_by_provider:
            latest_pr_by_provider[pr["provider_id"]] = pr["id"]

    # Fetch all locations for those requests in one query.
    pr_location_map = {}
    for loc in ProviderRequestLocation.objects.filter(
        request_id__in=latest_pr_by_provider.values()
    ).order_by("id"):
        pr_location_map.setdefault(loc.request_id, []).append(loc)

    to_create = []
    for hp in Hostingprovider.objects.all().iterator():
        if hp.id in providers_with_locations:
            continue

        pr_id = latest_pr_by_provider.get(hp.id)
        if pr_id:
            # Copy locations from the latest ProviderRequest
            pr_locations = pr_location_map.get(pr_id, [])
            for i, loc in enumerate(pr_locations):
                to_create.append(HostingProviderLocation(
                    hostingprovider=hp, name=loc.name, city=loc.city,
                    country=loc.country, is_primary=(i == 0),
                ))
        elif hp.country or hp.city:
            # Legacy provider with no request — use flat country/city
            to_create.append(HostingProviderLocation(
                hostingprovider=hp, city=hp.city or "",
                country=hp.country, is_primary=True,
            ))

    HostingProviderLocation.objects.bulk_create(to_create, batch_size=1000)
```

For each existing provider, the migration copies `ProviderRequestLocation`
rows from the latest `ProviderRequest` (first is marked `is_primary=True`).
For legacy providers with no request, it creates a single location from the
flat `country`/`city` fields. The migration is idempotent — it skips providers
that already have locations.

**`0116_create_link_disclosures_to_regions_flag.py`** — Creates the
`link_disclosures_to_regions` waffle flag, defaulting to off for all user
types.

### 4. The wizard: scoping disclosures to regions

The `CredentialForm` (used inside the evidence formset) gains two fields:

```python
# src/apps/accounts/forms/provider_request_wizard.py

class CredentialForm(AlwaysChangedModelFormMixin, forms.ModelForm):
    REGION_ALL = "all"
    REGION_SPECIFIC = "specific"

    region_scope = forms.ChoiceField(
        choices=[(REGION_ALL, "Apply to all my submitted regions"),
                 (REGION_SPECIFIC, "Apply to specific regions")],
        initial=REGION_ALL,
        required=True,
        widget=forms.RadioSelect(attrs={"class": "region-scope-radio"}),
    )

    locations = forms.MultipleChoiceField(
        choices=[],  # populated in __init__ from wizard session
        required=False,  # required only when region_scope == 'specific'
        widget=forms.SelectMultiple(attrs={"class": "disclosure-regions-select"}),
    )
```

The `region_scope` radio button lets the submitter choose between "all
regions" and "specific regions". When "specific" is selected, the `locations`
multi-select (enhanced with TomSelect's `checkbox_options` plugin — see ADR 2)
becomes visible.

The location choices are **not** PKs — they are **indices** into the list of
locations submitted in Step 1 of the wizard. This is because the locations
have not been saved to the database yet when the evidence step is rendered.
The wizard's `_get_location_choices()` method builds `(index, "Name, City, Country")`
tuples from the Step 1 formset data:

```python
# src/apps/accounts/views/provider/request/wizard.py

def _get_location_choices(self):
    """
    Build a list of (index, "City, Country") tuples from the LOCATIONS
    step's cleaned data. The indices correspond to the order of locations
    in the Step 1 formset, and are resolved to ProviderRequestLocation
    instances in done() after locations are saved.
    """
    location_step_data = self.get_cleaned_data_for_step(
        self.Steps.LOCATIONS.value
    )
    locations_formset = location_step_data.get("locations") if location_step_data else None
    if not locations_formset:
        return []

    location_choices = []
    for i, loc_data in enumerate(locations_formset):
        cd = loc_data.cleaned_data if hasattr(loc_data, "cleaned_data") else loc_data
        if cd.get("DELETE", False):
            continue
        city = cd.get("city", "")
        country = cd.get("country")
        name = cd.get("name", "")
        # Resolve country code to full name to match display_label
        country_name = country.name if hasattr(country, "name") else (
            countries.name(country) if country else ""
        )
        parts = [part for part in (name, city, country_name) if part]
        label = ", ".join(parts) if parts else f"Location {i + 1}"
        location_choices.append((str(i), label))
    return location_choices
```

The `done()` method resolves these indices to saved `ProviderRequestLocation`
instances and creates the through-model rows:

```python
# src/apps/accounts/views/provider/request/wizard.py

for form, evidence in saved_evidence_instances:
    ProviderRequestEvidenceLocation.objects.filter(evidence=evidence).delete()
    region_scope = form.cleaned_data.get("region_scope")
    if region_scope == "all":
        # Link to ALL of the provider's locations
        for location in pr_locations:
            ProviderRequestEvidenceLocation.objects.create(
                evidence=evidence, location=location,
            )
    elif region_scope == "specific":
        # Link to the selected locations (by index)
        selected_location_indices = form.cleaned_data.get("locations", [])
        for index_str in selected_location_indices:
            index = int(index_str)
            if 0 <= index < len(pr_locations):
                ProviderRequestEvidenceLocation.objects.create(
                    evidence=evidence, location=pr_locations[index],
                )
```

### 5. The approval flow: carrying links to live data

When a `ProviderRequest` is approved, the `approve()` method creates live
`HostingProviderLocation` rows from the draft `ProviderRequestLocation` rows,
then carries across the disclosure-region links:

```python
# src/apps/accounts/models/provider_request.py (approve method)

# Create live locations from submitted locations, replacing any existing ones.
hp.locations.all().delete()
request_locations = list(self.providerrequestlocation_set.all())
for i, location in enumerate(request_locations):
    HostingProviderLocation.objects.create(
        hostingprovider=hp,
        name=location.name,
        city=location.city,
        country=location.country,
        is_primary=(i == 0),
    )

# ... later, when creating supporting documents ...

# Build a mapping of draft location PKs -> live locations by index.
hp_locations = list(hp.locations.all().order_by("id"))
pr_locations = list(self.providerrequestlocation_set.all().order_by("id"))
loc_map = {}
for i, pr_loc in enumerate(pr_locations):
    if i < len(hp_locations):
        loc_map[pr_loc.pk] = hp_locations[i]

for evidence in self.providerrequestevidence_set.all().prefetch_related("locations"):
    supporting_doc = HostingProviderSupportingDocument.objects.create(
        hostingprovider=hp,
        title=evidence.title,
        # ... other fields ...
    )

    # Carry across disclosure-region links
    for evidence_location in evidence.locations.all():
        live_location = loc_map.get(evidence_location.pk)
        if live_location:
            HostingProviderSupportingDocumentLocation.objects.get_or_create(
                document=supporting_doc,
                location=live_location,
            )
```

The mapping is built **by index** (the Nth draft location maps to the Nth live
location) because the PKs change during approval — the draft and live models
are separate tables. The `get_or_create` call ensures idempotency if
`approve()` is called more than once.

### 6. The admin: read-only display

Both the hosting-provider admin and the provider-request admin display the
region scope as a read-only `region_scope_display` property:

```python
# src/apps/accounts/admin/hosting/provider.py

class HostingProviderLocationInline(admin.TabularInline):
    model = HostingProviderLocation
    extra = 0
    fields = ("name", "city", "country", "is_primary")
    ordering = ("-is_primary", "city")

class HostingProviderSupportingDocumentInline(admin.StackedInline):
    model = HostingProviderSupportingDocument
    readonly_fields = ("region_scope_display",)

    def get_queryset(self, request):
        # Prefetch locations so region_scope_display does not N+1
        return super().get_queryset(request).prefetch_related("locations")
```

The `region_scope_display` property on the model returns a human-readable
summary:

```python
@property
def region_scope_display(self) -> str:
    locations = self.locations.all()
    if not locations:
        return "Global"
    location_labels = [str(loc) for loc in locations]
    return f"Specific regions: {', '.join(location_labels)}"
```

### 7. The waffle flag

The `link_disclosures_to_regions` flag gates the UI in the wizard's evidence
step. When the flag is off:

- The `region_scope` and `locations` fields are popped from `CredentialForm`
  in `__init__`.
- The `clean()` method defaults `region_scope` to `"all"` and `locations` to
  `[]`, so `done()` automatically links evidence to all locations.
- The TomSelect init script in the evidence template is not rendered.

This means the flag can be turned on/off at runtime without code changes or
migrations, and the form behaves identically to the pre-feature version when
the flag is off.

## Why this is useful

1. **Disclosures can be scoped to specific regions.** A provider operating in
   three regions can now say "this energy certificate covers Amsterdam and
   Singapore, but not São Paulo." This gives users of the directory more
   granular, trustworthy information.

2. **Locations are first-class objects.** Instead of a single `country`/`city`
   string, a provider has a structured set of locations that can be queried,
   displayed, and linked to disclosures. The admin can add/remove/edit
   locations without touching the original request.

3. **The primary-location sync keeps legacy code working.** The flat
   `Hostingprovider.country`/`.city` fields are automatically kept in sync
   with the primary location. Directory pages, API responses, and exports that
   read those fields continue to work without modification.

4. **The draft/live split is clean.** Draft data (`ProviderRequest*`) is
   separate from live data (`HostingProvider*`). The `approve()` method is the
   single bridge between the two, and it carries across both locations and
   disclosure-region links.

5. **The feature is safely gated.** The waffle flag allows incremental rollout
   and instant rollback. When the flag is off, the form is byte-identical to
   the pre-feature version.

6. **The backfill migration is idempotent and efficient.** It uses bulk queries
   (not N+1 lookups) to find the latest request for each provider and copy
   locations, and it skips providers that already have locations.

## Consequences

### Positive

1. **Structured location data.** The `HostingProviderLocation` model gives us
   a proper one-to-many relationship between providers and locations, with
   names, cities, countries, and a primary flag. This replaces the single
   flat `country`/`city` pair that could not represent multi-region providers.

2. **Disclosure-region links are queryable.** Because the through models
   (`HostingProviderSupportingDocumentLocation`,
   `ProviderRequestEvidenceLocation`) are explicit with `unique_together`
   constraints, we can query "which disclosures cover region X?" or "which
   regions does disclosure Y cover?" without parsing free text.

3. **Admin can review but not accidentally mutate.** The `region_scope_display`
   field is read-only in both the hosting-provider admin and the
   provider-request admin. Staff can see the scope at a glance without
   risking data corruption through the inline formset (which omits M2M
   fields with explicit through models — a known Django limitation).

4. **The feature is reversible.** The waffle flag can be turned off at
   runtime. When off, `region_scope` defaults to `"all"` and `locations` to
   `[]`, so evidence is automatically linked to all locations. The migration
   is also reversible (the backfill's reverse function deletes all
   `HostingProviderLocation` rows).

### Negative

1. **Two parallel model hierarchies.** The draft side (`ProviderRequestLocation`,
   `ProviderRequestEvidenceLocation`) and the live side
   (`HostingProviderLocation`,
   `HostingProviderSupportingDocumentLocation`) have nearly identical structure.
   This is the same pattern already used for other draft/live models in the
   codebase (e.g. `ProviderRequestEvidence` → `HostingProviderSupportingDocument`),
   but it means the `approve()` method must carefully map between the two.

2. **The index-based location mapping in `approve()` is fragile.** Draft
   locations are mapped to live locations **by order/index**, not by a stable
   foreign key. If the order of locations changes between the draft and
   approval (e.g., due to a re-submission), the mapping could link disclosures
   to the wrong live locations. The `get_or_create` call prevents duplicate
   rows, but does not detect a mis-mapping. This is mitigated by the fact that
   `approve()` deletes all existing live locations first and recreates them
   in the same order as the draft locations.

3. **The admin cannot edit disclosure-region links inline.** Django's admin
   inline formsets omit M2M fields with explicit through models, so the
   `locations` field does not appear in the `ProviderRequestEvidenceInline`
   or `HostingProviderSupportingDocumentInline`. Staff can view the scope
   (via `region_scope_display`) but cannot change which regions a disclosure
   covers from the admin. This is a known Django limitation documented in
   the inline form code comments. Editing through-model rows requires a
   custom admin form or a future admin action.

4. **The `display_label` property is duplicated.** Both
   `ProviderRequestLocation.display_label` and
   `HostingProviderLocation.display_label` have identical logic. A future
   refactor could extract a shared mixin, but the two models are in different
   modules and the duplication is small (6 lines each).

5. **The wizard uses index-based choices, not PKs.** The `locations` field in
   `CredentialForm` uses `(str(index), label)` choices rather than PKs,
   because the locations have not been saved when the form is rendered. This
   means the `done()` method must resolve indices to `ProviderRequestLocation`
   instances manually. If the locations formset is modified between rendering
   and submission (e.g., a row is deleted client-side), the indices could be
   stale. The `done()` method guards against out-of-bounds indices, but a
   stale-but-valid index would link to the wrong location.

6. **The `mark_safe` in `render_as_regions` template filter.** The
   `render_as_regions` filter uses `mark_safe()` on labels derived from
   user-submitted location names. A malicious provider could submit a
   location name containing HTML that would be rendered unescaped in the
   preview. This should be addressed by escaping the individual labels before
   joining them, but currently is not.

### Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Index-based mapping in `approve()` links to wrong location | `approve()` deletes and recreates live locations in the same order; `get_or_create` prevents duplicates |
| Admin staff cannot edit region links | Documented as a known limitation; region links are editable through the wizard (on re-submission) or via Django shell |
| Waffle flag is off but existing data has region links | When the flag is off, `done()` defaults to `region_scope="all"` and links to all locations; existing through-model rows are not deleted, so a flag toggle does not lose data |
| Backfill migration fails on providers with no country or city | The migration checks `elif hp.country or hp.city` and only creates a legacy location if at least one field is non-empty; providers with neither are skipped |
| `display_label` returns `"Location {pk}"` for empty locations | This is a fallback for edge cases; the wizard's `_get_location_choices` uses `"Location {i+1}"` for unsaved locations, so the two fallbacks differ slightly |
| `mark_safe` on user-derived location names in `render_as_regions` | Should be addressed in a follow-up by escaping individual labels before joining |

## Verification

After implementing this change, the following was verified:

| Check | Result |
|-------|--------|
| `TestProviderRequestEvidenceLocation` | Through-model creation, unique constraint, cascade deletes, M2M access all pass |
| `TestHostingProviderSupportingDocumentLocation` | Live through-model creation and unique constraint pass |
| `TestHostingProviderLocation` | `is_primary` syncs flat fields, only one primary enforced, non-primary does not sync |
| `TestWizardSubmissionWithRegions` | `region_scope="all"` links to all locations; `region_scope="specific"` links only selected; flag-off defaults to all |
| `TestApprovalFlow` | `approve()` creates live `HostingProviderLocation` rows (first is primary, flat fields synced), carries across region links to live through-model rows |
| `TestAdminInlineLocations` | Inline form limits locations queryset to the request's locations |
| `TestCredentialFormClean` | Flag-off defaults to `all`; `specific` requires at least one location; `all` clears locations |

## References

- [Django many-to-many relationships with through models](https://docs.djangoproject.com/en/dev/topics/db/models/#extra-fields-on-many-to-many-relationships)
- [Django admin inlines and M2M with through models](https://docs.djangoproject.com/en/dev/topics/db/models/#django.db.models.ManyToManyField.through) — known limitation: admin omits M2M fields with explicit through models
- [django-waffle](https://waffle.readthedocs.io/) — feature flags for Django
- [django-countries `CountryField`](https://github.com/PyCQA/django-countries) — country field with ISO 3166-1 codes
- ADR 2: TomSelect for Autocomplete Multi-Selects — the disclosure-regions picker uses TomSelect's `checkbox_options` plugin
