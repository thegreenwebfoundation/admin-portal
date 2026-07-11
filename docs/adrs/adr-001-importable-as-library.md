# ADR 1: Making the Admin Portal Importable as a Library

## Status

Accepted

## Context

The Green Web Foundation admin portal is a Django application that is primarily
deployed as a running service. We clone the repository, install dependencies,
and run `./run_gunicorn.sh` and `./run_worker.sh` to serve it in production.

However, the project also encodes a rich **domain model** — hosting providers,
datacenters, green IP ranges, ASNs, green domains, provider requests, API keys,
carbon.txt motivations, and so on. This model is useful well beyond the running
application. We regularly want to:

- Write one-off analysis scripts against the live database.
- Explore data in [marimo](https://marimo.info) notebooks that depend on the
  ORM.
- Prototype new tooling that reuses the model, factories, importers, and
  business logic without standing up the full Django stack (gunicorn, RabbitMQ,
  etc.).

Before this change, the project was configured as an application only.
`pyproject.toml` declared `name = "admin-portal"` with no `[build-system]`
section. The `apps/` and `greenweb/` packages lived at the repository root and
were only importable because the repo root happened to be on `sys.path` when
running `manage.py` or `pytest`. There was no way to `pip install` the project
into an external environment.

### Requirements

1. The project must remain **primarily an application**. Deployment scripts,
   `manage.py` commands, `collectstatic`, `tailwind build`, `pytest`, and the
   Docker/Ansible deploy chain must continue to work unchanged from the repo
   root.
2. It must be installable as a **library** from a GitHub branch (not PyPI),
   using standard `uv`/`pip` dependency syntax, including the [PEP 723 inline
   dependency block](https://peps.python.org/pep-0723/) for marimo notebooks
   run in `--sandbox` mode.
3. After installing, a consumer must be able to initialise Django and query the
   ORM without standing up RabbitMQ, a cache server, or any HTTP layer:

   ```python
   import django
   django.setup()
   from apps.accounts.models import Hostingprovider
   Hostingprovider.objects.all().count()
   ```

4. The cost of this change should be low: existing import strings
   (`from apps.accounts.models import ...`, `INSTALLED_APPS = ["apps.accounts",
   ...]`, `name = "apps.accounts"` in `apps.py`) should not need to change.

### Options considered

We considered three layouts before settling on the chosen approach.

#### Option A — Flat layout with a `gwp/` namespace package

Keep `apps/` and `greenweb/` at the repo root and use `hatchling`'s
`force-include` to also copy them into `gwp/apps/` and `gwp/greenweb/` inside
the built wheel. Consumers would then write:

```python
from gwp.apps.accounts.models import Hostingprovider
```

**Rejected.** Django's app registry is keyed off the `name` attribute in each
app's `apps.py` (e.g. `AccountsConfig.name = "apps.accounts"`). When a model
class is defined, Django's `ModelBase.__new__` walks up the module's
`__name__` to find a matching installed app. A model imported via
`gwp.apps.accounts.models.hosting.abstract` has `__name__` starting with
`gwp.apps.`, which does not match `apps.accounts`, so Django raises:

```
RuntimeError: Model class gwp.apps.accounts.models.hosting.abstract.Label
doesn't declare an explicit app_label and isn't in an application in
INSTALLED_APPS.
```

We tried two workarounds before abandoning this option:

1. **`sys.modules` aliasing** in `gwp/__init__.py` (`sys.modules["gwp.apps"] =
   sys.modules["apps"]`). This lets `import gwp.apps.accounts` resolve, but
   Python still records the module's `__name__` as `gwp.apps.accounts...`,
   which is what Django checks. The models fail to register.

2. **A `sys.meta_path` import hook** that redirects `gwp.apps.*` imports to
   `apps.*` at load time. This fixes the `__name__` problem, but because
   `django.setup()` had already imported the models under `apps.accounts.*`,
   re-importing them under `gwp.apps.accounts.*` causes Django to register the
   same models a second time:

   ```
   RuntimeWarning: Model 'accounts.label' was already registered.
   ValueError: You can't have two TaggableManagers with the same through model.
   ```

The only clean way to make `gwp.apps.accounts.models` work would be to move the
source code into `gwp/apps/` and update every `apps.py` `name`, every
`INSTALLED_APPS` entry, every import string, and every migration reference — a
large, risky refactor for a project whose primary job is running as an
application, not being a library. We decided this was not worth the cost.

#### Option B — `src/gwp/` layout (full namespacing)

Move `apps/` and `greenweb/` under `src/gwp/`, update all import strings, and
ship a single namespaced `gwp` package.

**Rejected.** Same cost/benefit problem as Option A: hundreds of import strings
and Django app configs would need to change, and every open branch and PR would
conflict on merge. The namespace collision risk that `gwp.apps` is meant to
solve is not a real problem for us — our notebooks and one-off scripts control
their own environments, and we have no other package called `apps` in scope.

#### Option C — `src/` layout with flat packages _(chosen)_

Move `apps/` and `greenweb/` under `src/` (without a `gwp` namespace), declare
`packages = ["src/apps", "src/greenweb"]` in `pyproject.toml`, and add `src/`
to `sys.path` in `manage.py` and `conftest.py`. The distribution is named
`gwp`, but the import paths stay `apps.accounts.models` and
`greenweb.settings.*`.

**Selected.** This is the pattern used by [pretix](https://github.com/pretix/pretix),
a high-profile Django project that also ships both as an application and an
installable package. It required no changes to any import string, Django app
config, or migration, and it cleanly separates "what gets installed" (`src/`)
from "repo tooling" (`Dockerfile`, `ansible/`, `docs/`, `justfile`).

## Decision

We will adopt a **`src/` layout** and declare the project as the installable
distribution **`gwp`** (short for "Green Web Portal").

### 1. Directory structure

```
admin-portal/
├── src/
│   ├── apps/                ← Django apps (moved from repo root)
│   │   ├── accounts/
│   │   ├── greencheck/
│   │   └── theme/
│   └── greenweb/            ← Django project config (moved from repo root)
│       ├── settings/
│       │   ├── common.py
│       │   ├── development.py
│       │   ├── library.py   ← NEW: minimal settings for ORM-only usage
│       │   ├── production.py
│       │   ├── staging.py
│       │   └── testing.py
│       ├── urls.py
│       └── wsgi.py
├── manage.py                ← Updated: inserts src/ into sys.path
├── conftest.py              ← Updated: inserts src/ into sys.path
├── pyproject.toml           ← Updated: gwp, hatchling, src/ packages
├── Dockerfile               ← Updated: PYTHONPATH=/app/src
├── justfile                 ← Updated: src/apps/theme/static_src path
├── ansible/                 ← Updated: rollup chdir path
├── docs/
└── ...
```

### 2. `pyproject.toml`

The project is renamed from `admin-portal` to `gwp` and a `hatchling`
build system is added:

```toml
[project]
name = "gwp"
version = "0.1.0"
description = "Green Web Foundation admin portal - importable as a library"
# ...all existing dependencies unchanged...

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/apps", "src/greenweb"]
```

The distribution name `gwp` is taken on PyPI, but **we do not intend to publish
to PyPI**. Consumers install directly from a GitHub branch:

```python
# PEP 723 inline dependency block (marimo notebooks, uv scripts)
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "gwp @ git+https://github.com/thegreenwebfoundation/admin-portal.git@ca-admin-portal-as-gwp-library",
#     "python-dotenv>=1.0.1",
# ]
# ///
```

### 3. `manage.py` and `conftest.py` add `src/` to `sys.path`

So that running from the repo root still finds the packages:

```python
# manage.py
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))
```

```python
# conftest.py
SRC_DIR = pathlib.Path(__file__).parent / "src"
sys.path.insert(0, str(SRC_DIR))
```

### 4. New `greenweb/settings/library.py` for ORM-only usage

A new settings module is added for consumers who only need the ORM. It imports
from `common.py` and then:

- Removes `debug_toolbar`, `django_browser_reload`, and
  `whitenoise.runserver_nostatic` from `INSTALLED_APPS` (they are dev-only and
  not installed in a library environment).
- Removes `debug_toolbar`, `whitenoise`, `drf_api_logger`, and `basicauth`
  middleware (they require request/response cycles or dev-only apps).
- Overrides `DRAMATIQ_BROKER` to use `dramatiq.brokers.stub.StubBroker` so no
  RabbitMQ connection is needed.
- Overrides `CACHES` to use `DummyCache` so no cache backend is needed.
- Fixes the deprecated `GUARDIAN_MONKEY_PATCH` setting (renamed to
  `GUARDIAN_MONKEY_PATCH_USER` in newer django-guardian).

### 5. `ROOT` path calculation updated

`greenweb/settings/common.py` uses `environ.Path(__file__) - N` to find the
repo root. Since `common.py` moved one level deeper (from
`greenweb/settings/common.py` to `src/greenweb/settings/common.py`), `N`
changed from `3` to `4`:

```python
# ROOT is the project root (where manage.py lives)
# __file__ is at src/greenweb/settings/common.py, so we go up 4 levels
ROOT = environ.Path(__file__) - 4
```

### 6. `STATICFILES_DIRS` uses `ROOT()` for an absolute path

The previous relative path (`"apps/theme/static"`) broke when `collectstatic`
ran from a different working directory. It now uses:

```python
STATICFILES_DIRS = [
    ROOT("src/apps/theme/static"),
]
```

### 7. Dockerfile and Ansible paths updated

- `Dockerfile`: `PYTHONPATH=/app/src` (was `/app`); the rollup `cd` path
  becomes `./src/apps/theme/static_src/`.
- `ansible/_assemble_deploy_assets.yml`: the rollup `chdir` becomes
  `"{{ project_root }}/current/src/apps/theme/static_src"`.
- All other Ansible playbooks run `./manage.py` from
  `{{ project_root }}/current` and need no changes, because `manage.py` itself
  inserts `src/` into `sys.path`.

## Why we deliberately did NOT make this a "proper" PyPI library

Several decisions were made to keep the library surface small and avoid
over-engineering, since this project is **primarily an application** that
happens to be importable, not a library first.

### No PyPI publishing

Publishing to PyPI would require version bumping, release tooling, and a CI
release pipeline. Our consumers are a small number of internal notebooks and
scripts. Installing from a GitHub branch with
`"gwp @ git+https://...@branch"` is sufficient and avoids the release
overhead.

### No `gwp.*` import namespace

Renaming every `apps.*` and `greenweb.*` import to `gwp.apps.*` and
`gwp.greenweb.*` would have been the "clean" library approach, but it would
require updating every `apps.py` `name`, every `INSTALLED_APPS` entry, every
import string across the codebase, and every migration's `app_label`. The
collision risk of a top-level `apps` package is not a real problem for our
consumers (they control their own environments). We keep `apps.` and
`greenweb.` as the import paths.

### No separation of dev dependencies into "extras"

A library published to PyPI would typically split its dependencies into
`[project.dependencies]` (runtime) and a `dev` extra (testing, linting,
notebooks). We keep all runtime and dev dependencies together in one
`pyproject.toml` because our consumers are internal and the extra disk space
is negligible. This also means a consumer gets everything they need to run
`manage.py` commands (like `collectstatic` or `tailwind build`) without a
separate `pip install gwp[dev]` step.

### `library.py` keeps all apps (including UI apps)

We considered stripping UI-heavy apps (`tailwind`, `crispy_forms`,
`widget_tweaks`, `explorer`, `drf_yasg`) from `library.py` for speed. We chose
to keep them for safety: models with `ForeignKey` references to those apps
might fail to load if the app is uninstalled. The extra startup time is
acceptable for our use case.

### `library.py` only patches `GUARDIAN_MONKEY_PATCH` locally

The deprecated `GUARDIAN_MONKEY_PATCH = False` setting in `common.py` was not
renamed there (it would require testing the full application against the newer
django-guardian API). Instead, `library.py` sets the new
`GUARDIAN_MONKEY_PATCH_USER = False` and pops the deprecated name from
`globals()`, scoping the fix to library usage only.

## Code samples — using the project as a third-party library

### Standalone script (PEP 723 inline dependencies)

```python
# save as query_providers.py and run with: uv run query_providers.py
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "gwp @ git+https://github.com/thegreenwebfoundation/admin-portal.git@ca-admin-portal-as-gwp-library",
#     "python-dotenv>=1.0.1",
# ]
# ///

import os
from dotenv import load_dotenv

# Set DJANGO_SETTINGS_MODULE BEFORE loading .env, otherwise the .env file's
# DJANGO_SETTINGS_MODULE=greenweb.settings.development would override it.
os.environ["DJANGO_SETTINGS_MODULE"] = "greenweb.settings.library"

# Load DATABASE_URL, SECRET_KEY, and any other env vars the settings require.
load_dotenv("/path/to/your/.env")

import django
django.setup()

from apps.accounts.models import Hostingprovider

count = Hostingprovider.objects.all().count()
print(f"Total hosting providers: {count}")
```

### Marimo notebook in `--sandbox` mode

```python
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "gwp @ git+https://github.com/thegreenwebfoundation/admin-portal.git@ca-admin-portal-as-gwp-library",
#     "python-dotenv==1.2.2",
#     "marimo>=0.23.8",
# ]
# ///

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell
def _():
    import os
    from dotenv import load_dotenv

    os.environ["DJANGO_SETTINGS_MODULE"] = "greenweb.settings.library"
    load_dotenv(".env")  # place a .env next to the notebook

    import django
    django.setup()


@app.cell
def _():
    from apps.accounts.models import Hostingprovider
    Hostingprovider.objects.all().count()


if __name__ == "__main__":
    app.run()
```

Run with:

```bash
marimo edit --sandbox your_notebook.py
# or
uv run --with marimo marimo edit --sandbox your_notebook.py
```

### Key things to remember

1. **Import from `apps.` and `greenweb.`, not `gwp.`** — `gwp` is only the
   distribution name (what you `pip install`). The importable packages are
   `apps` and `greenweb`.
2. **Set `DJANGO_SETTINGS_MODULE=greenweb.settings.library`** before calling
   `django.setup()`, and set it before loading `.env` if your `.env` file
   overrides `DJANGO_SETTINGS_MODULE`.
3. **Provide a `DATABASE_URL`** — the library settings still need a real
   database to query. All other external services (RabbitMQ, cache, basic
   auth) are stubbed out.

## Consequences

### Positive

1. **The domain model is accessible from any Python environment.** Notebooks,
   ad-hoc scripts, and analysis tooling can `pip install` the project and query
   the ORM without standing up the full application stack.
2. **No external services required for library usage.** The `library.py`
   settings use a stub broker and dummy cache, so consumers don't need
   RabbitMQ or Redis running.
3. **Development workflow is unchanged.** `manage.py runserver`, `pytest`,
   `collectstatic`, `tailwind build`, `just test`, and the Docker/Ansible
   deploy chain all work exactly as before. The only visible difference is that
   source code lives under `src/` instead of at the repo root.
4. **Standard, idiomatic layout.** The `src/` layout matches pretix, a
   well-known Django project that also ships as both an application and a
   library. It cleanly separates installable code from repo tooling.
5. **No import strings changed.** Because we kept `apps.` and `greenweb.` as
   top-level import paths, existing code, migrations, `INSTALLED_APPS`
   references, and `apps.py` `name` attributes all remain valid. This keeps
   merge conflicts minimal and avoids touching Django's app registry.
6. **GitHub-branch installs work out of the box.** Consumers can pin to a
   specific branch, tag, or commit with standard `pip`/`uv` syntax — no PyPI
   release pipeline needed.

### Negative

1. **All file paths that were relative to the repo root needed updating.**
   Anything that referenced `apps/` or `greenweb/` on the filesystem (test
   fixtures, `STATICFILES_DIRS`, Dockerfile `cd` paths, Ansible `chdir`
   paths, the `ROOT` calculation in `common.py`) had to be updated to account
   for the extra `src/` level. We found and fixed these incrementally:
   - `STATICFILES_DIRS` now uses `ROOT("src/apps/theme/static")`.
   - Test fixtures in `test_importer_csv.py` and `test_form.py` now prepend
     `"src"` to their path construction.
   - The `ROOT` calculation changed from `environ.Path(__file__) - 3` to `- 4`.
2. **Two `sys.path` inserts are required.** `manage.py` and `conftest.py` both
   need to insert `src/` into `sys.path`. This is a small amount of "magic"
   that developers need to be aware of, though it is contained to two files
   and is a well-understood pattern.
3. **The distribution name doesn't match the import paths.** You `pip install
   gwp` but you `from apps.accounts.models import ...`. This is a minor
   cognitive cost. We judged it acceptable because the alternative (full
   `gwp.apps.*` namespacing) would require a large, risky refactor of Django
   app configs and every import string in the codebase.
4. **`library.py` duplicates some overrides from `testing.py`.** The stub
   broker and dummy cache settings exist in both files. A future refactor
   could extract a shared `minimal_services.py` base, but we chose not to
   premature-optimise this.
5. **Open branches may conflict on the file moves.** Because `apps/` and
   `greenweb/` were moved into `src/`, any branch that modifies files under
   those directories will need to rebase or merge carefully. This is a
   one-time cost.

### Risks and mitigations

| Risk | Mitigation |
|------|------------|
| New tests reference fixture paths with `settings.ROOT` and forget the `src/` level | Documented in this ADR; search for `settings.ROOT` when adding tests |
| Consumer installs `gwp` into an environment that also has a different package called `apps` | Deemed low-risk for our internal consumers; if it happens, we can revisit Option B |
| `library.py` drifts out of sync with `common.py` as new apps/middleware are added | `library.py` imports `*` from `common.py` and only filters, so new additions are picked up automatically unless they require an external service |
| `hatchling` build config breaks if directories are moved again | The `packages` list is explicit (`["src/apps", "src/greenweb"]`) and `uv build` is run as part of the library test script |

## Verification

After implementing this change, the following was verified:

| Check | Result |
|-------|--------|
| `uv run pytest src/apps/accounts/tests/ src/apps/greencheck/tests/` | 377 passed, 6 skipped, 0 failed |
| `python manage.py check` | "System check identified no issues (0 silenced)" |
| `python manage.py collectstatic --noinput --clear` | 589 static files copied |
| `python manage.py tailwind build` | Built `styles.css` |
| Library import from built wheel (fresh venv) | `Hostingprovider.objects.all().count() == 1336` |
| `marimo edit --sandbox notebook.py` with PEP 723 deps | Installable, ORM queries succeed |

## References

- [PEP 723 – Inline script metadata](https://peps.python.org/pep-0723/)
- [Hatchling build targets](https://hatch.pypa.io/latest/config/build/)
- [uv inline script dependencies](https://docs.astral.sh/uv/guides/scripts/)
- [pretix source layout](https://github.com/pretix/pretix) — `src/`-based Django
  project that ships as both an application and an installable package
- [wagtail source layout](https://github.com/wagtail/wagtail) — flat layout,
  included for comparison
- [Django app registry: `AppConfig.name`](https://docs.djangoproject.com/en/dev/ref/applications/#django.apps.AppConfig.name)
