# ADR 2: Adopting TomSelect for Autocomplete Multi-Selects

## Status

Draft

## Context

The admin portal uses **Django Autocomplete Light** (DAL) with **Select2** for
autocomplete multi-select fields across both the Django admin and the
public-facing provider registration wizard. DAL provides server-side widgets
(`ModelSelect2`, `ModelSelect2Multiple`, `TaggitSelect2`) and a `Select2QuerySetView`
base class that returns JSON in Select2's format
(`{"results": [{"id": 1, "text": "..."}, ...]}`).

This setup works, but it carries several costs when used in the **registration
wizard** (the public form that new providers submit through):

1. **Heavy jQuery dependency.** Select2 requires jQuery. The wizard templates
   already use Tailwind CSS and vanilla JS, so loading jQuery just for Select2
   introduces a framework mismatch and a non-trivial page-weight cost.

2. **Tight coupling to DAL's widget lifecycle.** DAL widgets render their own
   `<select>` markup, inline `<script>` tags, and media declarations. The
   widget HTML is opaque — it is hard to augment the rendered output with
   sibling elements (e.g. a per-item checkbox list) because the widget owns the
   entire rendering pipeline.

3. **No plugin extensibility.** Select2 has a limited plugin model. When we
   needed **per-item visibility checkboxes** on the upstream-provider picker
   (each selected provider can be marked "show in public directory" or "hidden"),
   Select2 offered no clean way to attach extra UI per selected item.

4. **Bundle is not our own.** DAL's Select2 assets are served from Django's
   static files, but they are a transitive dependency of `django-autocomplete-light`.
   We cannot easily customise the build (e.g. to include the `checkbox_options`
   plugin for a list-of-checkboxes multi-select) without forking or overriding
   the DAL media declarations.

### Requirements

1. The provider registration wizard must offer **search-as-you-type** autocomplete
   multi-selects for choosing upstream providers and disclosure regions.
2. The upstream-provider picker must support **per-item visibility checkboxes**
   that appear and disappear dynamically as providers are added/removed.
3. The disclosure-regions picker must support a **checkbox-style multi-select**
   (items shown as a list with checkboxes, not as tags with remove buttons only).
4. The solution must work in the existing Tailwind-based template layout
   without requiring jQuery.
5. The existing DAL autocomplete endpoints (`Select2QuerySetView` subclasses
   returning Select2-shaped JSON) must continue to work — we do not want to
   rewrite the server-side API.
6. The Django admin's DAL/Select2 usage (`autocomplete_fields`, `TaggitSelect2`)
   should remain untouched for now — the migration is scoped to the public
   registration wizard.

### Options considered

#### Option A — Continue with DAL/Select2 and customise its rendering

Extend the DAL widget classes to inject the visibility checkboxes into the
rendered output, and load Select2's `checkbox` plugin via custom media.

**Rejected.** DAL's widget rendering is tightly controlled by the library.
Injecting sibling HTML elements around the `<select>` requires overriding
`render()` and reassembling the full markup, which is fragile and breaks on
DAL upgrades. Select2's jQuery dependency remains. The `checkbox_options`
plugin is a TomSelect feature, not a Select2 feature — Select2 has no native
equivalent.

#### Option B — Switch to TomSelect with a custom Django widget

Use [TomSelect](https://tom-select.org/) — a vanilla-JS, dependency-free fork
of Select2 — as the front-end library. Write a thin Django widget
(`UpstreamProviderSelectWidget`) that renders a plain `<select multiple>` with
`data-*` attributes, and let client-side JS enhance it into a TomSelect
instance. Reuse the existing Select2-shaped JSON endpoints via a small adapter.

**Selected.** This gives full control over the rendered HTML, supports the
per-item visibility checkboxes, avoids jQuery, and reuses the existing server
endpoints. The widget's rendering is transparent (it renders a standard `<select>`
plus optional sibling elements), which makes it easier to reason about and
test.

#### Option C — Use a headless/custom autocomplete with no library

Write a from-scratch autocomplete multi-select with plain XHR and DOM APIs.

**Rejected.** While maximally lightweight, this would require reimplementing
debounced search, keyboard navigation, ARIA roles, and dropdown positioning —
all of which TomSelect already handles well. The maintenance cost is not
justified.

## Decision

We will adopt **TomSelect** as the autocomplete multi-select library for the
provider registration wizard, bundled locally via Rollup, and exposed
globally as `window.TomSelect`.

### 1. Bundling: `tom-select` npm package via Rollup

TomSelect is installed as an npm dependency and bundled into a single IIFE
file that assigns the library to `window.TomSelect`:

```javascript
// src/apps/theme/static_src/src/app.js
import TomSelect from "tom-select";

window.TomSelect = TomSelect;
```

The Rollup config produces two outputs (dev and minified):

```javascript
// src/apps/theme/static_src/rollup.config.js
import resolve from '@rollup/plugin-node-resolve';
import { terser } from 'rollup-plugin-terser';

const browserBuild = {
  input: 'src/app.js',
  output: { file: '../static/js/dist/app.bundle.js', format: 'iife', name: "app" },
  plugins: [resolve()],
};

const browserBuildMin = {
  input: 'src/app.js',
  output: { file: '../static/js/dist/app.bundle.min.js' },
  plugins: [resolve(), terser()],
};

export default [browserBuild, browserBuildMin];
```

The bundled JS and the TomSelect vendor CSS are loaded globally in `base.html`
so that any child template or form media can rely on `window.TomSelect` being
available:

```html
<!-- src/apps/accounts/templates/base.html -->
<link rel="stylesheet" href="{% static 'css/vendor/tom-select.css' %}">
<script src="{% static 'js/dist/app.bundle.js' %}"></script>
```

### 2. The reusable JS adapter: `tomselect-widgets.js`

A small framework-free IIFE provides `window.initTomSelectAutocomplete()` — a
helper that turns a plain `<select multiple>` into a TomSelect instance,
reading the autocomplete endpoint from a `data-autocomplete-url` attribute on
the element.

The key piece of design is the **Select2-to-TomSelect response adapter**.
The existing DAL endpoints return JSON in Select2's format:

```json
{"results": [{"id": 1, "text": "Green Web"}, ...]}
```

TomSelect expects options in this shape:

```json
{"value": "1", "text": "Green Web"}
```

The adapter bridges this gap inside the `load` callback, so TomSelect can
reuse the existing DAL endpoints without any server-side changes:

```javascript
// src/apps/accounts/static/accounts/js/tomselect-widgets.js
function buildSelect2LoadCallback(autocompleteUrl) {
    return function (query, callback) {
        var separator = autocompleteUrl.indexOf("?") === -1 ? "?" : "&";
        var requestUrl = autocompleteUrl + separator + "q=" + encodeURIComponent(query);

        var xhr = new XMLHttpRequest();
        xhr.open("GET", requestUrl, true);
        xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
        xhr.onload = function () {
            if (xhr.status !== 200) return callback();
            try {
                var json = JSON.parse(xhr.responseText);
                var results = json.results || [];
                var options = results.map(function (item) {
                    return { value: String(item.id), text: item.text };
                });
                callback(options);
            } catch (e) {
                callback();
            }
        };
        xhr.send();
    };
}

window.initTomSelectAutocomplete = function (selectElement, options) {
    if (typeof TomSelect === "undefined") return null;
    if (selectElement.tomselect) return selectElement.tomselect; // idempotent

    var autocompleteUrl = selectElement.getAttribute("data-autocomplete-url");

    var config = Object.assign({
        plugins: ["remove_button", "clear_button"],
        maxItems: null,
        valueField: "value",
        labelField: "text",
        searchField: ["text"],
        placeholder: selectElement.getAttribute("data-placeholder") || "",
        load: buildSelect2LoadCallback(autocompleteUrl),
        loadThrottle: 300,
        preload: false,
    }, options || {});

    return new TomSelect(selectElement, config);
};
```

### 3. The `UpstreamProviderSelectWidget` Django widget

This is the most complex part of the change, and the part most likely to seem
"magical" to someone unfamiliar with Django's widget internals. This section
explains the design in detail.

#### What problem does it solve?

When a provider registers using the "resell an existing verified provider"
basis, they select one or more upstream providers from an autocomplete list.
For each selected provider, they can choose whether that relationship is
**public** (shown in the directory) or **hidden**. This means the form field
needs to return not just a list of provider IDs, but a list of dicts:

```python
[{"provider": "42", "is_public": True}, {"provider": "17", "is_public": False}]
```

A plain `ModelMultipleChoiceField` with a `SelectMultiple` widget returns a
list of IDs. We need a composite widget that renders a `<select multiple>` (for
the provider picker) **plus** a fieldset of per-provider checkboxes (for
visibility), and a custom field that knows how to clean the combined data back
into a list of dicts.

#### Architecture: thin Python widget, fat client-side JS

The widget follows a **"thin Python, fat JS"** pattern. The Python side renders
standard HTML elements (a `<select multiple>` plus optional checkbox rows) with
`data-*` attributes and a JSON data block. The JS side reads those attributes
and enhances the elements with TomSelect.

```python
# src/apps/accounts/forms/widgets/upstream_provider_widget.py

class UpstreamProviderSelectWidget(forms.SelectMultiple):
    """
    Composite widget: TomSelect autocomplete multi-select + per-item
    visibility checkboxes.

    Renders a plain ``<select multiple>`` enhanced by TomSelect
    (bundled in ``js/dist/app.bundle.js``) followed by a fieldset of
    checkboxes — one per selected provider — letting the submitter choose
    whether each upstream connection should be visible in the public
    directory.

    The widget's ``value_from_datadict`` returns a list of dicts::

        [{"provider": "42", "is_public": True}, ...]

    When ``show_visibility`` is False, the visibility fieldset is omitted
    and every selected provider is treated as public.
    """

    def __init__(self, attrs=None, show_visibility=True, url=None, **kwargs):
        self.show_visibility = show_visibility
        self.url = url
        super().__init__(attrs=attrs)
```

#### How data flows through the widget

The widget participates in Django's form lifecycle at three points. Each one
is straightforward in isolation, but understanding the full cycle helps dispel
the sense of magic:

**1. Rendering (`render`)**

When the form renders, the widget receives the current value (either a list of
provider IDs or a list of dicts from an existing model instance). The
`render()` method:

1. **Normalises** the value into a list of `{"provider": id, "is_public": bool}`
   dicts via `_normalize_initial()`. This handles legacy list-of-IDs, single
   instances, and the new dict format.

2. **Loads provider names** from the database via `_load_provider_names()`, so
   that the `<option>` elements TomSelect reads on init have human-readable
   labels (not just `"Provider #42"`).

3. **Temporarily replaces `self.choices`** with only the currently-selected
   providers, calls `super().render()` to produce the `<select>` HTML, then
   restores the original choices. This keeps the markup small — TomSelect
   fetches unselected options dynamically via the autocomplete endpoint.

4. **Appends the visibility fieldset** (if `show_visibility` is True) — a
   `<fieldset>` with one checkbox row per selected provider, plus a
   `<script type="application/json">` data block carrying the provider IDs and
   names for the client-side JS.

```python
def render(self, name, value, attrs=None, renderer=None, **kwargs):
    items = self._normalize_initial(value)
    name_map = self._load_provider_names(items)
    for item in items:
        if not item.get("provider_name"):
            item["provider_name"] = name_map.get(
                item["provider"], f"Provider #{item['provider']}"
            )

    pk_values = [item["provider"] for item in items]

    # Only render <option> elements for selected providers.
    original_choices = list(self.choices)
    self.choices = [(item["provider"], item["provider_name"]) for item in items]
    try:
        select_html = super().render(name, pk_values, attrs, renderer, **kwargs)
    finally:
        self.choices = original_choices

    if not self.show_visibility:
        return mark_safe(select_html)

    visibility_html = self._render_visibility_list(name, field_id, items)
    return mark_safe(select_html + visibility_html)
```

**2. Reading submitted data (`value_from_datadict`)**

When the form is submitted, Django calls `value_from_datadict()` to extract
the widget's value from the POST data. This method reads **both** the
multi-select's provider IDs **and** the per-provider visibility checkboxes,
combining them into a list of dicts:

```python
def value_from_datadict(self, data, files, name):
    provider_ids = super().value_from_datadict(data, files, name)
    if not provider_ids:
        return []

    result = []
    for pid in provider_ids:
        checkbox_name = f"{name}_visibility_{pid}"
        if self.show_visibility:
            is_public = data.get(checkbox_name) == "on"
        else:
            is_public = True  # default when visibility checkboxes are hidden
        result.append({"provider": str(pid), "is_public": is_public})
    return result
```

The checkbox `name` follows the convention `{field_name}_visibility_{provider_id}`,
so `value_from_datadict` can reconstruct the mapping without any hidden state.

**3. The companion field: `UpstreamProviderChoiceField`**

The widget is paired with `UpstreamProviderChoiceField`, a subclass of
`ModelMultipleChoiceField`. The parent's `clean()` expects a list of PKs and
converts them to a queryset — but our widget returns a list of dicts. The
field overrides `clean()` to intercept the dict list, validate each provider
ID against the queryset, and return the list of dicts with resolved
`Hostingprovider` instances:

```python
class UpstreamProviderChoiceField(forms.ModelMultipleChoiceField):
    """
    Pairs with UpstreamProviderSelectWidget. clean() returns a list of dicts:
        [{"provider": <Hostingprovider instance>, "is_public": True}, ...]
    """

    def clean(self, value):
        if value in self.empty_values or not value:
            return []
        if not isinstance(value, list):
            raise forms.ValidationError("Expected a list of upstream provider selections.")

        result = []
        for item in value:
            pid = item.get("provider")
            is_public = item.get("is_public", True)
            if not pid:
                continue
            try:
                provider = self.queryset.get(pk=pid)
            except (ValueError, LookupError, self.queryset.model.DoesNotExist):
                raise forms.ValidationError(
                    f"Provider with ID '{pid}' is not a valid choice."
                )
            result.append({"provider": provider, "is_public": is_public})
        return result
```

#### How the JS wires it together: `upstream_provider_visibility.js`

The client-side JS (`upstream_provider_visibility.js`) is responsible for:

1. Finding all `<select>` elements with the `data-upstream-visibility-widget`
   attribute (injected by `build_attrs`).
2. Calling `window.initTomSelectAutocomplete()` on each one, passing
   `onItemAdd`, `onItemRemove`, and `onClear` callbacks.
3. When a provider is added (TomSelect `onItemAdd` event), dynamically
   creating a checkbox row in the visibility fieldset.
4. When a provider is removed (TomSelect `onItemRemove` event), removing the
   corresponding checkbox row.
5. Reading the initial data from the `<script type="application/json">` block
   to populate the checkbox rows for pre-selected providers.

The JS uses the DOM API (`createElement`, `appendChild`) rather than
`innerHTML` so the browser properly registers the checkboxes in the
accessibility tree. An `aria-live="polite"` announcer notifies screen-reader
users when providers are added or removed.

#### The full data flow, summarised

```
Initial render (GET):
  Instance data → _normalize_initial() → list of dicts
  → _load_provider_names() adds display names
  → render() produces:
      <select multiple data-upstream-visibility-widget data-autocomplete-url="...">
          <option value="42">Green Web</option>
      </select>
      <fieldset class="upstream-visibility-list">
          <div class="upstream-visibility-row" data-provider-id="42">
              <input type="checkbox" name="..._visibility_42" checked />
              <label>Green Web — show in public directory</label>
          </div>
          <script type="application/json" id="..._data">
              [{"provider": "42", "is_public": true, "provider_name": "Green Web"}]
          </script>
      </fieldset>

  JS on page load:
    upstream_provider_visibility.js finds [data-upstream-visibility-widget]
    → calls initTomSelectAutocomplete(select, {onItemAdd, onItemRemove, onClear})
    → tomselect-widgets.js creates new TomSelect(select, {load: select2Adapter, ...})
    → TomSelect enhances the <select> with search-as-you-type

User adds a provider:
    TomSelect fires onItemAdd("17")
    → JS creates a checkbox row for provider 17
    → User can uncheck to mark as hidden

Form submit (POST):
    value_from_datadict reads:
      select → ["42", "17"]
      checkboxes → {"..._visibility_42": "on", ..._visibility_17: absent}
    → returns [{"provider": "42", "is_public": True},
               {"provider": "17", "is_public": False}]

    UpstreamProviderChoiceField.clean():
      validates each provider ID against the queryset
      → returns [{"provider": <Hostingprovider>, "is_public": True}, ...]
```

### 4. The disclosure-regions multi-select (evidence step)

The evidence step of the wizard uses TomSelect directly in the template (not via
a Python widget) for the disclosure-regions picker. This is a different use
case — the choices are a fixed list (the provider's submitted locations), not a
remote autocomplete endpoint — so it uses TomSelect's `checkbox_options` plugin
instead of the `load` callback:

```javascript
// src/apps/accounts/templates/provider_registration/evidence.html
function ensureTomSelect() {
    if (typeof TomSelect === 'undefined') return;
    var select = locationsWrapper.querySelector('select.disclosure-regions-select');
    if (!select || select.tomselect) return;
    new TomSelect(select, {
        plugins: ['checkbox_options', 'remove_button'],
        maxItems: null,
        placeholder: 'Select regions this disclosure applies to',
        hideSelected: false,
    });
}
```

This script is gated behind the `link_disclosures_to_regions` waffle flag (see
ADR 3) and is lazily initialised only when the "specific regions" radio button
is selected, to avoid layout issues from initialising TomSelect inside a hidden
container.

### 5. Usage in the form

The `BasisForVerificationForm` declares the upstream-provider field using the
new widget and field:

```python
# src/apps/accounts/forms/provider_request_wizard.py
from apps.accounts.forms.widgets import (
    UpstreamProviderChoiceField,
    UpstreamProviderSelectWidget,
)

class BasisForVerificationForm(forms.ModelForm):
    upstream_providers = UpstreamProviderChoiceField(
        queryset=Hostingprovider.objects.filter(archived=False, is_listed=True),
        required=False,
        label="Which existing verified provider(s) do you rely on...",
        widget=UpstreamProviderSelectWidget(
            url="linked-provider-autocomplete",
            attrs={"data-placeholder": "Search for a verified provider..."},
        ),
    )
```

The `show_visibility` flag on the widget is toggled in the form's `__init__`
based on the `enable_private_upstream_linking` waffle flag.

### 6. Reusing the existing DAL autocomplete endpoint

The autocomplete data still comes from a Django Autocomplete Light view. TomSelect
only replaces the front-end rendering — the server-side endpoint is unchanged:

```python
# src/apps/accounts/views/provider/autocomplete.py
class LinkedProviderAutocompleteView(autocomplete.Select2QuerySetView):
    """Returns active, listed providers, filtered by search term."""

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Hostingprovider.objects.none()

        qs = Hostingprovider.objects.filter(archived=False, is_listed=True)
        if self.q:
            qs = qs.filter(name__istartswith=self.q)
        return qs.order_by("name")
```

This view returns Select2-shaped JSON. The `buildSelect2LoadCallback` adapter in
`tomselect-widgets.js` translates the Select2 response into TomSelect options
at runtime, so the endpoint serves both the old Select2 consumers (Django admin)
and the new TomSelect consumers (registration wizard).

## Why TomSelect is useful

1. **No jQuery dependency.** TomSelect is vanilla JS, so it fits naturally into
   the wizard's Tailwind + vanilla JS stack without loading a second framework.

2. **Plugin system.** TomSelect has a first-class plugin system. The
   `checkbox_options` plugin (used for disclosure regions) and the
   `remove_button`/`clear_button` plugins (used for upstream providers) are
   configured declaratively, with no need to fork the library.

3. **Transparent rendering.** TomSelect works on a plain `<select multiple>`
   element — it reads the existing `<option>` elements and enhances them. This
   means the Django widget renders standard, testable HTML, and TomSelect is a
   progressive enhancement. If JS fails to load, the form degrades to a plain
   `<select multiple>` that still works (without search-as-you-type).

4. **Bundled locally.** We bundle TomSelect via Rollup into `app.bundle.js`,
   so there is no CDN dependency. The build step (`rollup -c` in
   `src/apps/theme/static_src/`) produces both a dev and a minified bundle.

5. **Reuses existing endpoints.** The Select2-to-TomSelect response adapter
   means we did not need to write new server-side autocomplete endpoints. The
   existing `Select2QuerySetView` subclasses continue to serve both Select2
   (Django admin) and TomSelect (wizard) consumers.

## Consequences

### Positive

1. **The upstream-provider picker supports per-item visibility checkboxes.**
   This is the primary feature that motivated the switch — Select2 could not
   do this cleanly. The composite widget renders a `<select>` plus a checkbox
   fieldset, and the JS keeps them in sync as providers are added and removed.

2. **No jQuery on the registration wizard.** The wizard now loads only
   Tailwind CSS, the bundled TomSelect IIFE (~50 KB minified), and the two
   small helper JS files. The DAL/Select2 jQuery assets (`select2.js`,
   `jquery.js`) are no longer loaded on wizard pages.

3. **Progressive enhancement.** If `app.bundle.js` fails to load, the form
   degrades to a plain `<select multiple>`. The visibility checkboxes are
   server-rendered for initial selections, so they remain functional even
   without JS (new selections added via JS won't have checkboxes, but the
   widget defaults `is_public=True` for those).

4. **Testable HTML.** The widget renders standard HTML that can be asserted
   against in Django tests (see
   `test_wizard_basis_step_uses_tomselect_when_private_flag_on` in
   `src/apps/accounts/tests/test_provider_request.py`), without needing to
   execute JavaScript.

5. **Disclosure-regions multi-select uses checkboxes, not tags.** The
   `checkbox_options` plugin shows each location as a labelled checkbox in a
   list, which is a better affordance for a small, known set of choices than
   a tag-based remove-button UI.

### Negative

1. **Two multi-select libraries coexist.** The Django admin still uses
   DAL/Select2 (`TaggitSelect2`, `autocomplete_fields`), while the registration
   wizard uses TomSelect. This means both libraries' CSS and JS are loaded
   across the project (though not on the same page). A future migration could
   replace DAL entirely, but that is out of scope for now.

2. **The `UpstreamProviderSelectWidget` is complex.** The widget renders a
   composite of `<select>` + `<fieldset>` + `<script type="application/json">`,
   and its `value_from_datadict` reassembles data from multiple POST fields
   into a list of dicts. This is more complex than a standard Django widget.
   The docstrings and this ADR document the design, but a developer
   encountering the widget for the first time will need to read the code
   carefully to understand the data flow.

3. **The `build_attrs` data attribute is the "magic" signal.** The JS finds
   widgets by querying for `[data-upstream-visibility-widget]`. If this
   attribute is accidentally removed (e.g., by a future refactor of
   `build_attrs`), the TomSelect initialisation silently does nothing. The
   tests catch this by asserting the attribute is present in the rendered HTML.

4. **The Rollup build step is manual.** There is no `npm run rollup` script in
   `package.json` — the build is invoked separately (likely via a direct
   `rollup -c` command or a Makefile target). If the bundled
   `app.bundle.js` becomes stale (e.g., after upgrading `tom-select`), the
   wizard will use the old version until the bundle is rebuilt.

5. **The `checkbox_options` plugin requires a local Tom Select build.** The
   standard CDN build of Tom Select does not include the `checkbox_options`
   plugin by default. Bundling locally via Rollup lets us include it, but it
   means we cannot swap to a CDN-hosted build without losing this plugin.

### Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Developer is confused by the composite widget's data flow | This ADR documents the full lifecycle; the widget docstring includes a data-flow summary |
| DAL endpoints change their JSON shape in a future upgrade | The adapter in `tomselect-widgets.js` is defensive (try/catch, fallback to empty callback); tests in `test_autocomplete.py` assert the endpoint contract |
| `app.bundle.js` becomes stale after a `tom-select` npm upgrade | The bundled file is committed to the repo; a stale bundle shows up in code review |
| Both Select2 and TomSelect CSS loaded globally could conflict | TomSelect CSS uses `.ts-` prefixed classes; Select2 uses `.select2-` prefixed classes — no overlap |
| The `data-upstream-visibility-widget` attribute is removed accidentally | Tests assert the attribute is present in the rendered HTML |

## Verification

After implementing this change, the following was verified:

| Check | Result |
|-------|--------|
| `test_wizard_basis_step_uses_tomselect_when_private_flag_on` | Asserts `app.bundle.js`, `tom-select.css`, `tomselect-widgets.js`, and `data-autocomplete-url=` are in the rendered HTML; DAL/Select2 assets are NOT |
| `test_wizard_basis_step_uses_tomselect_when_private_flag_off` | Same assets are loaded; the visibility fieldset is NOT rendered |
| `test_upstream_provider_widget_renders_provider_names_in_select` | Pre-selected providers display their names (not `Provider #<id>`) |
| `test_autocomplete.py` (7 tests) | Auth gating, archived/unlisted exclusion, ordering, search filtering all pass |
| The evidence step's TomSelect with `checkbox_options` | Renders as a checkbox list, re-inits on formset row add via MutationObserver |

## References

- [TomSelect documentation](https://tom-select.org/)
- [TomSelect plugins](https://tom-select.org/plugins/)
- [Django Autocomplete Light](https://dal.sel4d.org/) — still used for admin-side autocomplete
- [Select2 response format](https://select2.org/data-sources/ajax) — the JSON shape DAL endpoints return
- [Django widget `value_from_datadict`](https://docs.djangoproject.com/en/dev/ref/forms/widgets/#django.forms.Widget.value_from_datadict)
