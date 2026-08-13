# Plan: Private Upstream Provider Linking

## Context

Currently, when a provider lists upstream providers (providers they rely on for green energy claims), **all** upstream connections are always visible publicly in the directory. We want to introduce a per-connection visibility flag that defaults to **public**, but can be set to **hidden**.

### Key Design Decisions

1. **Submitter controls visibility** in the wizard — each selected upstream can be individually marked as hidden (defaults to public).
2. **Existing data** → all migrated to `is_public=True` (no behaviour change). **New admin-created** connections default to `is_public=False`.
3. **Downstream view** in admin shows public/hidden state.

---

## Current Architecture

### Data Model

- `Hostingprovider.upstream_providers` — `ManyToManyField("self", symmetrical=False)` with an auto-generated through table (`src/apps/accounts/models/hosting/provider.py:300-307`).
- `ProviderRequest.upstream_providers` — `ManyToManyField(Hostingprovider)` with an auto-generated through table (`src/apps/accounts/models/provider_request.py:153-159`).
- When a request is approved, `ProviderRequest.approve()` copies upstreams to the live provider via `hp.upstream_providers.set(self.upstream_providers.all())` (`src/apps/accounts/models/provider_request.py:321`).

### Admin UI

- `HostingproviderAdmin` shows `upstream_providers` in a fieldset using Select2 autocomplete (`autocomplete.ModelSelect2Multiple`), wired in `HostingAdminForm.Meta.widgets` (`src/apps/accounts/forms/admin.py:35-38`).
- `ProviderRequestAdmin` shows `upstream_providers` as a read-only field (`src/apps/accounts/admin/provider_request.py:75`).
- Downstream providers shown via read-only `display_downstream_providers` method (`src/apps/accounts/admin/hosting/provider.py:620-630`).

### Wizard

- Step 3 (`BasisForVerificationForm`) in `src/apps/accounts/forms/provider_request_wizard.py:146-331` has an `upstream_providers` `ModelMultipleChoiceField` with a `ModelSelect2Multiple` widget pointing at the `linked-provider-autocomplete` URL.
- The wizard template (`src/apps/accounts/templates/provider_registration/basis_for_verification.html`) uses JS to show/hide the upstream picker based on whether the "reseller" verification basis is selected.
- The preview step uses a `render_as_upstream_providers` template filter (`src/apps/accounts/templatetags/preview_extras.py:50-65`) to display selected provider names.
- The wizard `done()` method (`src/apps/accounts/views/provider/request/wizard.py:250-252`) saves upstream providers via `pr.upstream_providers.set(upstream_providers)`.

### Public Directory

- `src/apps/theme/templates/greencheck/partials/_directory_results.html:60-71` iterates `obj.upstream_providers.all` and shows each upstream name. Gated behind the `upstream_providers` waffle flag.

### Provider Portal

- `src/apps/accounts/templates/provider_portal/request_detail.html:114-127` shows the request's upstream providers in a table.

---

## The Widget Challenge

The current wizard uses `autocomplete.ModelSelect2Multiple`, which renders a single Select2 multi-select tag input. It cannot express per-item metadata (like a public/hidden toggle per selected provider). We need a different approach.

### Options Considered

#### Option A: Custom Composite Widget (recommended)

Create a custom Django widget that pairs the Select2 autocomplete with a per-item checkbox. The component renders as:
1. A Select2 autocomplete to **add** providers (same as now).
2. Below it, a list of selected providers, each with a checkbox: `[x] Show publicly` / `[ ] Hide`.

**How it works:**
- The widget's `render()` outputs a hidden multi-select (for Select2 compatibility) plus a container `<div>` that JS populates with one row per selected provider, each containing a checkbox.
- The widget's `value_from_datadict()` reads both the provider IDs and the checkbox states, returning a list of dicts like `[{"provider": 42, "is_public": True}, {"provider": 17, "is_public": False}]`.
- JS hooks into Select2's `change` event to add/remove rows in the visibility list when items are selected/deselected.

**Pros:** Single form field, no formset complexity, works within the existing wizard step naturally, clean UX, preserves the Select2 tag UX.
**Cons:** Custom widget code + JS to maintain (~150 lines total).

#### Option B: Inline Formset in the Wizard

Swap the `ModelMultipleChoiceField` for an inline formset. Each form row has: provider (Select2) + is_public checkbox.

**Pros:** Pure Django, no custom widget JS.
**Cons:** Formsets inside `SessionWizardView` are awkward — the wizard stores `form_list` not formsets. The preview step would need rework. The add/remove row UX needs a separate "add another" button + JS. Each form row having its own Select2 dropdown is odd UX.

### Decision: Option A (Custom Composite Widget)

Preserves the existing Select2 tag UX the user already knows, keeps the wizard form structure unchanged (still a single field), and only adds a visibility list beneath it. The admin uses an inline (which is a different context and naturally suited to formsets).

---

## Implementation

### 1. Data Model

**New through model** in `src/apps/accounts/models/hosting/provider.py`:

```python
class UpstreamProvider(TimeStampedModel):
    parent = models.ForeignKey(
        Hostingprovider, on_delete=models.CASCADE, related_name="upstream_connections"
    )
    upstream = models.ForeignKey(
        Hostingprovider, on_delete=models.CASCADE, related_name="downstream_connections"
    )
    is_public = models.BooleanField(default=True)

    class Meta:
        unique_together = ("parent", "upstream")
```

**Update `Hostingprovider.upstream_providers`** (line 300) to add `through=UpstreamProvider`.

**New through model** for `ProviderRequest` in `src/apps/accounts/models/provider_request.py`:

```python
class ProviderRequestUpstreamProvider(TimeStampedModel):
    request = models.ForeignKey(
        ProviderRequest, on_delete=models.CASCADE, related_name="upstream_connections"
    )
    upstream = models.ForeignKey(Hostingprovider, on_delete=models.CASCADE)
    is_public = models.BooleanField(default=True)

    class Meta:
        unique_together = ("request", "upstream")
```

**Update `ProviderRequest.upstream_providers`** (line 153) to use `through=ProviderRequestUpstreamProvider`.

We need both through models because `ProviderRequest` points to `Hostingprovider` (not to itself like `Hostingprovider` does).

### 2. Migrations

- Create migration adding both through models.
- **Data migration** to move rows from the auto-generated M2M tables into the new through tables, with `is_public=True` for all existing rows:
  - `hostingprovider_upstream_providers` (columns: `from_hostingprovider_id`, `to_hostingprovider_id`)
  - `providerrequest_upstream_providers` (columns: `providerrequest_id`, `hostingprovider_id`)
- Then alter the M2M fields to add `through=`, using `SeparateDatabaseAndState` (since the underlying data has already been migrated).

### 3. Admin UI — Hosting Provider

**Replace the Select2 autocomplete field** with a `TabularInline` in `src/apps/accounts/admin/hosting/provider.py`:

```python
class UpstreamProviderInline(admin.TabularInline):
    model = UpstreamProvider
    fk_name = "parent"
    extra = 1
    autocomplete_fields = ["upstream"]
    fields = ("upstream", "is_public")
```

- Register this inline in `HostingproviderAdmin.inlines` (only for existing objects).
- Remove `upstream_providers` from the `linked_by_fieldset` (lines 557-565), replacing it with just `display_downstream_providers`.
- Remove the `upstream_providers` widget from `HostingAdminForm.Meta.widgets` in `src/apps/accounts/forms/admin.py` (lines 35-38), since the inline now handles it.

**Admin default (`is_public=False` for new connections):** Override the inline form's `__init__` to set `initial={'is_public': False}` for unbound extra forms, while existing rows load their saved value. Existing connections (migrated to `is_public=True`) display with their saved value — only truly new rows added via the inline's "extra" form default to `False`.

**Update `display_downstream_providers`** (lines 620-630) to show the visibility state of each downstream connection:

```
Provider A (public)
Provider B (hidden)
```

### 4. Admin UI — Provider Request

In `src/apps/accounts/admin/provider_request.py`:

- Remove `"upstream_providers"` from `readonly_fields` (line 75) and replace with a custom read-only display method:

```python
@admin.display(description="Upstream providers")
def display_upstream_providers(self, obj):
    connections = obj.upstream_connections.select_related("upstream")
    if not connections:
        return "None"
    return mark_safe("<br>".join(
        f"{c.upstream.name} ({'public' if c.is_public else 'hidden'})"
        for c in connections
    ))
```

- Add `display_upstream_providers` to `readonly_fields`.

### 5. Wizard Form Changes

In `src/apps/accounts/forms/provider_request_wizard.py` (`BasisForVerificationForm`):

**Replace** the `upstream_providers` field (lines 165-177) with a field using the new custom composite widget:

```python
upstream_providers = forms.ModelMultipleChoiceField(
    queryset=Hostingprovider.objects.filter(archived=False, is_listed=True),
    required=False,
    label="Which existing verified provider(s) do you rely on as the basis for the claim of using green energy?",
    help_text="...",
    widget=UpstreamProviderSelectWidget(
        url="linked-provider-autocomplete",
        attrs={"data-placeholder": "Search for a verified provider..."},
    ),
)
```

**New custom widget** in `src/apps/accounts/forms/widgets/upstream_provider_widget.py`:

```python
class UpstreamProviderSelectWidget(autocomplete.ModelSelect2Multiple):
    """
    Composite widget: Select2 autocomplete + per-item visibility checkboxes.
    Renders a hidden Select2 multi-select and a JS-driven list of selected
    providers, each with a 'show publicly' checkbox.
    """
    template_name = "accounts/widgets/upstream_provider_select.html"

    def value_from_datadict(self, data, files, name):
        # Returns list of {"provider": pk, "is_public": bool} dicts
        provider_ids = super().value_from_datadict(data, files, name)
        result = []
        for pid in provider_ids:
            key = f"{name}_visibility_{pid}"
            is_public = data.get(key, "on") == "on"
            result.append({"provider": pid, "is_public": is_public})
        return result
```

**Update `clean()`** (lines 315-327): changed data shape — upstreams are now a list of dicts, clear to empty list when no resell basis selected.

**Update `__init__`** (lines 222-225): populate initial data from through model connections instead of `instance.upstream_providers.all()`:

```python
if instance:
    self.initial["upstream_providers"] = [
        {"provider": c.upstream_id, "is_public": c.is_public}
        for c in instance.upstream_connections.all()
    ]
```

**Update wizard `done()`** (wizard.py lines 250-252): instead of `pr.upstream_providers.set(upstream_providers)`, create through-model instances:

```python
for item in upstream_providers:
    ProviderRequestUpstreamProvider.objects.get_or_create(
        request=pr,
        upstream_id=item["provider"],
        defaults={"is_public": item["is_public"]},
    )
```

**Update `get_initial_dict()`** (wizard.py line 624): populate initial from through model:

```python
"upstream_providers": [
    {"provider": c.upstream_id, "is_public": c.is_public}
    for c in hp_instance.upstream_connections.all()
]
```

### 6. Wizard Template Changes

**New widget template** `src/apps/accounts/templates/accounts/widgets/upstream_provider_select.html`:
- Renders the Select2 hidden select.
- Renders a `<div class="upstream-visibility-list">` that JS populates when providers are selected.
- Each row: `<label><input type="checkbox" name="..._visibility_{pk}" checked /> Show publicly</label>`

**New JS** (in the widget template or in `basis_for_verification.html`):
- Hook into Select2's `select2:select` event → add a visibility row with provider name + checkbox.
- Hook into `select2:unselect` → remove the corresponding row.
- Each visibility row has the provider name (from the selected option) + a checkbox.

**Update `basis_for_verification.html`:**
- The existing `toggleUpstreamProvidersSection()` JS (lines 50-69) references `#id_3-upstream_providers_helptext`. This stays the same — it shows/hides the parent container.
- Update the disclosure warning text (lines 13-19): currently says "if you do not wish for this relationship to be public, then please select another basis for verification." Update to reflect that relationships can now be individually marked as hidden.

### 7. Preview Template Changes

**Update `render_as_upstream_providers` filter** in `src/apps/accounts/templatetags/preview_extras.py` (lines 50-65): the value is now a list of `{"provider": pk, "is_public": bool}` dicts instead of a flat list of IDs. Update to show provider name + visibility state:

```python
@register.filter
def render_as_upstream_providers(value):
    if not value:
        return None
    provider_ids = [item["provider"] for item in value]
    providers = {p.id: p for p in Hostingprovider.objects.filter(id__in=provider_ids)}
    list_items = format_html_join(
        "",
        "<li>{} ({})</li>",
        (
            (providers[item["provider"]].name, "public" if item["is_public"] else "hidden")
            for item in value
        ),
    )
    return format_html("<ul>{}</ul>", list_items)
```

The preview in `_preview.html` will then show "[hidden]" next to hidden providers.

### 8. Approval Flow

Update `ProviderRequest.approve()` (line 321 in `provider_request.py`):

```python
# Replace: hp.upstream_providers.set(self.upstream_providers.all())
for conn in self.upstream_connections.all():
    UpstreamProvider.objects.get_or_create(
        parent=hp,
        upstream=conn.upstream,
        defaults={"is_public": conn.is_public},
    )
```

This preserves the visibility choice from the request into the live provider.

### 9. Public Directory Filtering

In `src/apps/theme/templates/greencheck/partials/_directory_results.html` (lines 60-71), change to only show public upstreams:

```django
{% if obj.upstream_providers.exists %}
    <div class="my-4">
        <p class="text-sm text-neutral-600 mb-1">Relies on:</p>
        <ul class="pl-0">
            {% for upstream in obj.upstream_providers.filter(upstreamprovider__is_public=True) %}
                <li class="service-label inline-block bg-neutral-200">{{ upstream.name }}</li>
            {% endfor %}
        </ul>
    </div>
{% endif %}
```

Better: add a property on `Hostingprovider`:

```python
@property
def public_upstream_providers(self):
    return self.upstream_providers.filter(upstreamprovider__is_public=True)
```

### 10. Provider Portal Request Detail

Update `src/apps/accounts/templates/provider_portal/request_detail.html` (lines 114-127): change the loop from `object.upstream_providers.all` to `object.upstream_connections.all`, showing each provider + its visibility state:

```django
{% if object.upstream_connections.exists %}
    {% for conn in object.upstream_connections.select_related("upstream").all %}
        {{ conn.upstream.name }} ({{ conn.is_public|yesno:"public,hidden" }})<br>
    {% endfor %}
{% else %}
    -
{% endif %}
```

### 11. Tests

| Test file | Lines | Changes |
|---|---|---|
| `test_models.py` | 218-261 | Update M2M tests for through-model semantics |
| `test_admin.py` | 420-579 | Update admin tests for inline UI + visibility toggle |
| `test_provider_request.py` | 670-721, 2444-3090+ | Update wizard tests for new widget data format, approval flow |
| `test_directory.py` | 132-167 | Add test: hidden upstreams don't appear in directory |

---

## Summary of Changes

| Layer | Change |
|---|---|
| **Models** | `UpstreamProvider` + `ProviderRequestUpstreamProvider` through models with `is_public` field |
| **Migrations** | Add through tables, data migration from auto M2M tables (`is_public=True`), alter fields |
| **Admin (Hosting Provider)** | Replace Select2 field with `TabularInline`, admin default `is_public=False` for new rows |
| **Admin (Provider Request)** | Replace readonly field with custom display showing visibility |
| **Wizard form** | New `UpstreamProviderSelectWidget` (Select2 + per-item checkbox) |
| **Wizard template** | Updated JS to show/hide, updated disclosure text, new widget template |
| **Preview** | Updated filter to show visibility state |
| **Approval flow** | `approve()` creates through-model rows preserving `is_public` |
| **Public directory** | Filter by `is_public=True` |
| **Provider portal** | Show visibility state in request detail |
| **Tests** | Update all affected tests |

---

## File Inventory

### New files
- `src/apps/accounts/forms/widgets/__init__.py`
- `src/apps/accounts/forms/widgets/upstream_provider_widget.py` — custom composite widget
- `src/apps/accounts/templates/accounts/widgets/upstream_provider_select.html` — widget template

### Modified files
- `src/apps/accounts/models/hosting/provider.py` — add `UpstreamProvider` through model, update M2M field
- `src/apps/accounts/models/provider_request.py` — add `ProviderRequestUpstreamProvider` through model, update M2M field, update `approve()`
- `src/apps/accounts/admin/hosting/provider.py` — replace fieldset with TabularInline, update `display_downstream_providers`
- `src/apps/accounts/admin/provider_request.py` — replace readonly field with display method
- `src/apps/accounts/forms/admin.py` — remove `upstream_providers` from `Meta.widgets`
- `src/apps/accounts/forms/provider_request_wizard.py` — use new widget, update `clean()`, initial data, save logic
- `src/apps/accounts/views/provider/request/wizard.py` — update `done()` and `get_initial_dict()`
- `src/apps/accounts/templates/provider_registration/basis_for_verification.html` — update disclosure text, JS references
- `src/apps/accounts/templates/provider_registration/partials/_preview.html` — no change needed (filter handles rendering)
- `src/accounts/templatetags/preview_extras.py` — update `render_as_upstream_providers` for new data shape
- `src/apps/theme/templates/greencheck/partials/_directory_results.html` — filter by `is_public=True`
- `src/apps/accounts/templates/provider_portal/request_detail.html` — show visibility state

### New migrations
- `src/apps/accounts/migrations/0XXX_add_upstream_provider_through_models.py`

---

## Accessibility Considerations for the Widget

The custom composite widget must be fully usable without a mouse and accessible to screen reader users. Select2 itself has some built-in ARIA support, but the per-item visibility checkboxes we're adding need deliberate handling.

### Problems to Solve

1. **Keyboard navigation of the visibility list** — the dynamically added visibility rows (one per selected provider) need to be reachable via Tab.
2. **Screen reader announcements** — when a provider is selected via the Select2 dropdown, a screen reader user needs to know that a visibility checkbox appeared and what it controls.
3. **No hidden interactive elements** — the visibility checkboxes must never be hidden via `display: none` or `visibility: hidden` (which removes them from the tab order and accessibility tree). If the upstream section is collapsed (no reseller basis selected), the checkboxes should be removed from the DOM or disabled, not visually hidden.
4. **Focus management on add/remove** — when a provider is selected or removed, focus should move predictably.
5. **No mouse-only JS handlers** — all JS must respond to keyboard events, not just `click`.

### Changes Required

#### A. Widget Template — ARIA attributes and semantic HTML

The widget template (`src/apps/accounts/templates/accounts/widgets/upstream_provider_select.html`) must render:

1. **The Select2 container** — inherits Select2's existing ARIA roles. No change needed, but the underlying `<select>` element must remain in the DOM (Select2 wraps a real `<select>`).

2. **The visibility list** — rendered as a semantic fieldset/list with proper labelling:

```html
<!-- Container for dynamically added visibility rows -->
<fieldset class="upstream-visibility-list mt-4" aria-label="Visibility of selected upstream providers">
    <legend class="text-sm font-medium mb-2">
        Selected providers — show publicly?
    </legend>
    <!-- JS inserts one row per selected provider here -->
    <!-- Each row is rendered as: -->
    <div class="upstream-visibility-row flex items-center gap-2 mb-2">
        <input
            type="checkbox"
            name="{field_name}_visibility_{provider_pk}"
            id="id_{field_name}_visibility_{provider_pk}"
            checked
            class="form-checkbox"
        />
        <label for="id_{field_name}_visibility_{provider_pk}">
            {provider_name} — show in public directory
        </label>
    </div>
</fieldset>
```

Key attributes:
- `aria-label` on the `<fieldset>` describes the group context.
- Each checkbox has a `<label>` with `for=` pointing to the checkbox `id` — this is the most robust way to associate them, works for both click-to-toggle and screen reader announcement.
- The label text includes the provider name and what "show publicly" means, so screen reader users hear context like "Acme Green Hosting — show in public directory".

#### B. JS — Keyboard-safe event handling

The JS that syncs the Select2 widget with the visibility rows must:

1. **Respond to Select2 events, not DOM clicks** — Select2 emits `select2:select` and `select2:unselect` for both mouse and keyboard interactions, so the JS already works for keyboard users. No `click`-only handlers needed.

2. **Manage focus when rows are added/removed:**
   - When a provider is **selected** (added), **do not** auto-move focus to the new checkbox — this is disruptive mid-flow. The user continues with Select2 to add more providers, then Tabs down to the checkboxes naturally.
   - When a provider is **removed** (deselected), if focus was on the corresponding checkbox, move focus to the next checkbox in the list, or to the Select2 input if no checkboxes remain. This prevents focus from falling into a void.

3. **Add/remove rows via DOM, not innerHTML** — use `document.createElement` and `appendChild`/`removeChild` so the browser properly registers the new elements in the accessibility tree. Avoid `innerHTML` string concatenation which can cause subtle focus/ordering bugs.

4. **No `display: none` for the visibility fieldset itself** — the visibility checkbox list is only rendered when at least one provider is selected (rows are added/removed dynamically). The `<fieldset>` can start empty; it doesn't need to be hidden. When the entire upstream section is collapsed (no reseller basis), the existing `toggleUpstreamProvidersSection()` JS hides the parent container. This should be changed from `style.display = "none"` to either:
   - Setting `hidden` attribute on the container, which reactively removes it from tab order and accessibility tree, or
   - Leaving the container in the DOM but disabled. The `hidden` attribute is the correct approach — it's the HTML semantic for "this content is not currently relevant" and correctly removes elements from the tab order and accessibility tree, unlike `display: none` set via JS which is equivalent but less clear to maintainers.

5. **Keyboard shortcut for toggling** — each checkbox is a standard `<input type="checkbox">`, so it's natively focusable via Tab and toggleable via Space. No custom key handler needed.

#### C. Screen Reader Live Announcements

When the user selects a provider via the Select2 dropdown, a screen reader user benefits from a live region announcement that a new visibility checkbox appeared. Add a visually-hidden `aria-live="polite"` region:

```html
<div class="sr-only" aria-live="polite" id="{field_name}_visibility_announcer">
    <!-- JS updates this when rows are added/removed -->
    <!-- e.g. "Acme Green Hosting added. You can choose whether to show this provider publicly." -->
</div>
```

The JS updates this region's `textContent` when:
- A provider is selected: `"{provider_name} added. Use the checkbox below to control visibility."`
- A provider is removed: `"{provider_name} removed."`

This uses the existing `sr-only` utility class already present in the codebase (`src/apps/theme/static_src/src/css/custom/forms-custom.css:121`).

#### D. Initial Render with Pre-existing Selections

When the form loads with existing upstream connections (edit flow), the visibility rows must be rendered server-side in the widget template, not injected via JS on page load. This ensures:
- Screen readers encounter the checkboxes in the initial DOM, before any JS runs.
- No flash of missing content.
- Works even if JS fails to load.

The widget template should iterate over the initial value (list of `{"provider": pk, "is_public": bool}`) and render the checkbox rows server-side. JS only handles rows added/removed after page load via the Select2 dropdown.

#### E. Admin Inline (no special handling needed)

The admin TabularInline uses standard Django admin rendering — checkboxes and autocomplete fields in a table. The Django admin is already keyboard-accessible for inline rows (Tab through fields, Space to toggle checkboxes). No additional work needed beyond what Django provides.

#### F. Reduced Motion

If any animation is added for rows appearing/disappearing (e.g. a fade-in), wrap it in a `@media (prefers-reduced-motion: reduce)` query to disable it for users who have motion sensitivity enabled. This is a low-effort inclusion:

```css
@media (prefers-reduced-motion: reduce) {
    .upstream-visibility-row {
        animation: none !important;
        transition: none !important;
    }
}
```

### Testing Checklist

Verify with:
- **Keyboard only:** Tab to the Select2, type to search, Enter to select, Tab to reach the visibility checkbox, Space to toggle, Tab to continue.
- **NVDA + Firefox (Windows):** Navigating to the upstream section announces "Selected providers — show publicly? grouping". Selecting a provider announces via the live region. Checkbox label reads provider name + "show in public directory".
- **VoiceOver + Safari (macOS):** Same flow. Landmarks announced correctly.
- **High contrast / zoom 200%:** Checkbox + label remain legible and in the tab order at 200% zoom.
- **JS disabled:** Pre-rendered visibility rows (for edit flow) are still present and functional as standard checkboxes. The Select2 search won't work, but the `<select>` element is still usable as a fallback multi-select.
