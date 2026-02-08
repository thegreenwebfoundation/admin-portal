# Migration Plan: Converting admin-portal to a Packaged Application

## Executive Summary

This document outlines a plan to convert the Green Web Foundation admin-portal Django project from a standard application to a **packaged application** that can be imported as a library by other Python projects, particularly Marimo notebooks for data analysis.

## Current State

The admin-portal is a Django web application with:
- **Package structure**: `apps/` directory containing `accounts`, `greencheck`, and `theme` Django apps
- **Settings**: `greenweb/settings/` with environment-specific modules (common, development, testing, production, staging)
- **Dependencies**: Managed via `uv` with `pyproject.toml` and `uv.lock`
- **Deployment**: Ansible-based deployment to production servers using systemd
- **Testing**: pytest with pytest-django, running against MySQL/MariaDB

### Key Files
```
admin-portal/
├── pyproject.toml          # Project metadata and dependencies
├── uv.lock                 # Locked dependencies
├── manage.py               # Django management script
├── conftest.py             # pytest configuration and fixtures
├── apps/
│   ├── __init__.py
│   ├── accounts/           # User accounts, providers, datacenters
│   └── greencheck/         # Domain checking, green domains, IP ranges
└── greenweb/
    ├── settings/           # Django settings modules
    ├── urls.py
    └── wsgi.py
```

## Goal

Enable importing admin-portal models and utilities in external projects:

```python
# Example: In a Marimo notebook
import marimo as mo

# Initialize Django for the admin-portal project
from greenweb import setup_django
setup_django()

# Now import models
from apps.greencheck.models import GreenDomain, GreencheckIp
from apps.accounts.models import Hostingprovider, Datacenter

# Query the database
green_domains = GreenDomain.objects.filter(green=True)[:100]
providers = Hostingprovider.objects.filter(archived=False)
```

## Trade-offs Analysis

### Benefits

1. **Code Reuse**: Marimo notebooks can use existing models, validators, and utilities without duplication
2. **Type Safety**: IDE autocompletion and type hints work across projects
3. **Consistency**: Analysis code uses the same data access patterns as the application
4. **Testing**: Shared test utilities and factories become available
5. **Maintainability**: Single source of truth for model definitions

### Drawbacks & Risks

1. **Django Configuration Complexity**
   - External projects must configure Django settings before importing models
   - Database connection strings must be provided
   - Some settings (INSTALLED_APPS, middleware) may conflict

2. **Dependency Bloat**
   - Importing the package pulls in all dependencies (Django, DRF, etc.)
   - Marimo notebooks may only need a subset of functionality

3. **Breaking Changes Risk**
   - Changes to models affect both the web app and analysis notebooks
   - Need careful versioning and changelog management

4. **Environment Coupling**
   - Analysis notebooks need access to the same database
   - Environment variables must be coordinated

5. **Deployment Unchanged**
   - Production deployment remains the same (Ansible, systemd)
   - The packaging is primarily for development/analysis use

## Migration Complexity Assessment

**Estimated Effort: Low to Medium**

The migration is relatively straightforward because:
- Project already uses `pyproject.toml` and `uv`
- Code is well-organized in `apps/` directory
- No complex build steps for the Python package itself
- Tests already use pytest-django with proper Django configuration

Main work involves:
1. Adding package metadata to `pyproject.toml`
2. Creating a setup helper module
3. Creating a settings module for library usage
4. Updating documentation

## Migration Steps

### Phase 1: Update pyproject.toml for Packaging

Modify `pyproject.toml` to declare the package structure:

```toml
[project]
name = "admin-portal"
version = "0.1.0"
description = "Green Web Foundation Admin Portal - Django application and data models"
readme = "README.md"
requires-python = ">=3.11"
# ... existing dependencies ...

[project.optional-dependencies]
analysis = [
    "marimo>=0.9.14",
    "pandas>=2.2.3",
    "numpy>=2.1.3",
]

[tool.uv]
dev-dependencies = [
    # ... existing dev dependencies ...
]

# Add package discovery
[tool.setuptools.packages.find]
where = ["."]
include = ["apps*", "greenweb*"]
```

### Phase 2: Create Django Setup Helper

Add to `greenweb/__init__.py` (currently empty):

```python
"""greenweb package initialization.

Provides utilities for using admin-portal as a library.
"""
import os
import sys
from pathlib import Path


def setup_django(
    settings_module: str = "greenweb.settings.analysis",
    database_url: str | None = None,
):
    """
    Configure Django for library usage.
    
    Call this before importing any Django models.
    
    Args:
        settings_module: Django settings module path. Defaults to analysis settings.
        database_url: Database connection URL. If not provided, reads from DATABASE_URL env var.
    
    Example:
        >>> from admin_portal import setup_django
        >>> setup_django(database_url="mysql://user:pass@localhost/greencheck")
        >>> from apps.greencheck.models import GreenDomain
    """
    import django
    
    # Add the project root to Python path if not already there
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Set database URL if provided
    if database_url:
        os.environ["DATABASE_URL"] = database_url
    
    # Set Django settings module
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
    
    # Initialize Django
    if not django.apps.apps.ready:
        django.setup()


def get_read_only_connection():
    """
    Get a read-only database connection for analysis.
    
    Uses DATABASE_URL_READ_ONLY if available, otherwise falls back to DATABASE_URL.
    """
    import os
    return os.environ.get("DATABASE_URL_READ_ONLY", os.environ.get("DATABASE_URL"))
```

### Phase 3: Create Analysis-Specific Settings

Create `greenweb/settings/analysis.py`:

```python
"""Django settings optimized for analysis/library usage.

This settings module is designed for read-only data analysis use cases,
such as Marimo notebooks, without the full web application stack.
"""
import os
import environ
import pathlib

# Minimal environ setup
ROOT = environ.Path(__file__) - 3
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, "analysis-mode-secret-key"),
    DATABASE_URL=(str, os.getenv("DATABASE_URL", "sqlite:///analysis.db")),
    DATABASE_URL_READ_ONLY=(str, os.getenv("DATABASE_URL_READ_ONLY")),
)

# Load .env file if present
dotenv_file = pathlib.Path(ROOT) / ".env"
if dotenv_file.exists():
    environ.Env.read_env(str(dotenv_file))

# Core settings
SECRET_KEY = env("SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = []

# Minimal installed apps - just what's needed for models
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django_countries",
    "django_mysql",
    "taggit",
    "guardian",
    "apps.accounts",
    "apps.greencheck",
]

# Database configuration
DATABASES = {
    "default": env.db("DATABASE_URL"),
}

# Add read-only replica if configured
if env("DATABASE_URL_READ_ONLY"):
    DATABASES["readonly"] = env.db("DATABASE_URL_READ_ONLY")

# Minimal middleware
MIDDLEWARE = []

# Time zone
TIME_ZONE = "UTC"
USE_TZ = True

# Auth settings required by django-guardian
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
]

# Custom user model (required for apps.accounts)
AUTH_USER_MODEL = "accounts.User"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

### Phase 4: No Directory Changes Needed

The existing flat layout works. No need to create an `admin_portal/` directory or move to a `src/` layout.

Just add the setup helper directly to `greenweb/__init__.py` (currently empty):

```python
# greenweb/__init__.py
from .setup import setup_django  # noqa
```

Or inline the function directly in `greenweb/__init__.py` if you prefer fewer files.

### Phase 5: Add Type Hints Marker

Create `py.typed` files to enable type hints:

```bash
touch apps/py.typed
touch apps/accounts/py.typed
touch apps/greencheck/py.typed
touch greenweb/py.typed
```

### Phase 6: Update Tests

Add tests for the library interface:

```python
# tests/test_library_usage.py
import pytest
import os


class TestLibraryUsage:
    """Test that the package can be used as a library."""

    def test_setup_django_initializes_correctly(self):
        """Test that setup_django properly initializes Django."""
        # This test should run in a fresh Python process ideally
        from greenweb import setup_django
        
        # Should not raise
        setup_django(settings_module="greenweb.settings.testing")
        
        import django
        assert django.apps.apps.ready

    def test_models_importable_after_setup(self):
        """Test that models can be imported after Django setup."""
        from greenweb import setup_django
        setup_django(settings_module="greenweb.settings.testing")
        
        from apps.greencheck.models import GreenDomain, GreencheckIp, GreencheckASN
        from apps.accounts.models import Hostingprovider, Datacenter
        
        # Models should be importable
        assert GreenDomain is not None
        assert Hostingprovider is not None
```

### Phase 7: Documentation Updates

Update README.md to document library usage:

```markdown
## Using as a Library

The admin-portal can be imported as a Python package for data analysis:

### Installation

```bash
# Install with analysis extras
uv pip install -e ".[analysis]"

# Or add as a dependency in your project
uv add admin-portal --git https://github.com/thegreenwebfoundation/admin-portal.git
```

### Usage in Marimo Notebooks

```python
import marimo as mo

# Initialize Django
from admin_portal import setup_django
setup_django(database_url="mysql://user:pass@localhost/greencheck")

# Import models
from apps.greencheck.models import GreenDomain
from apps.accounts.models import Hostingprovider

# Query data
domains = GreenDomain.objects.filter(green=True).values('url', 'hosted_by', 'modified')[:1000]
df = pd.DataFrame(domains)
```
```

## Sample Marimo Notebook

Here's a complete example notebook (`data-analysis/starter-notebook.py`):

```python
import marimo

__generated_with = "0.9.14"
app = marimo.App(width="medium")


@app.cell
def __():
    import marimo as mo
    import os
    
    # Set database connection - use read-only replica for safety
    os.environ.setdefault(
        "DATABASE_URL", 
        "mysql://readonly:password@db.example.com/greencheck"
    )
    
    return mo, os


@app.cell
def __(os):
    # Initialize Django
    import sys
    sys.path.insert(0, "/path/to/admin-portal")  # Adjust path as needed
    
    from admin_portal import setup_django
    setup_django()
    
    print("Django initialized successfully!")
    return setup_django,


@app.cell
def __():
    import pandas as pd
    from django.db import connection
    
    # Import models after Django setup
    from apps.greencheck.models import GreenDomain, GreencheckIp
    from apps.accounts.models import Hostingprovider, Datacenter
    
    return GreenDomain, GreencheckIp, Hostingprovider, Datacenter, pd


@app.cell
def __(GreenDomain, pd):
    # Query green domains
    green_domains_qs = GreenDomain.objects.filter(
        green=True
    ).values(
        'url', 'hosted_by', 'hosted_by_website', 'modified'
    )[:10000]
    
    green_domains_df = pd.DataFrame(list(green_domains_qs))
    green_domains_df


@app.cell
def __(Hostingprovider, pd):
    # Query hosting providers
    providers_qs = Hostingprovider.objects.filter(
        archived=False
    ).values(
        'name', 'country', 'website', 'partner', 'is_listed'
    )
    
    providers_df = pd.DataFrame(list(providers_qs))
    providers_df


@app.cell
def __(green_domains_df, mo):
    # Visualize green domains by provider
    top_providers = green_domains_df.groupby('hosted_by').size().nlargest(20)
    
    mo.ui.chart(
        data=top_providers.reset_index(name='count'),
        x='hosted_by',
        y='count',
        kind='bar',
        title='Top 20 Green Hosting Providers by Domain Count'
    )


@app.cell
def __(GreenDomain):
    # Example: Using domain checker directly
    from apps.greencheck.domain_check import GreenDomainChecker
    
    checker = GreenDomainChecker()
    # result = checker.check_domain("example.com")  # Would perform actual lookup
    
    print("Domain checker available for analysis")


if __name__ == "__main__":
    app.run()
```

## Changes to Deployment

### No Changes Required

The production deployment via Ansible remains unchanged. The packaging changes are additive and don't affect:

- `ansible/deploy.yml` - Still deploys the full application
- `ansible/deploy-workers.yml` - Background workers unchanged
- systemd service configuration - No modifications needed
- Docker builds - `Dockerfile` works as before

### CI/CD Considerations

Add a new test job to verify library usage:

```yaml
# .github/workflows/test.yml (addition)
  test-library-usage:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.12"
      - name: Install package
        run: |
          pip install uv
          uv pip install -e ".[analysis]"
      - name: Test import
        run: |
          python -c "
          from greenweb import setup_django
          setup_django(settings_module='greenweb.settings.testing')
          from apps.greencheck.models import GreenDomain
          print('Library import successful')
          "
```

## Alternative Approaches Considered

### 1. Separate Models-Only Package

Extract just the Django models into a separate `greenweb-models` package.

**Pros:**
- Smaller dependency footprint
- Cleaner separation

**Cons:**
- Duplicated code to maintain
- Models can drift from application
- More complex release process

### 2. Database-Only Access (No Django)

Use SQLAlchemy directly in notebooks, bypassing Django entirely.

**Pros:**
- No Django configuration needed
- Lighter weight

**Cons:**
- Loses Django ORM benefits (validation, relationships)
- Must duplicate model logic
- No access to domain checker utilities

### 3. API-Based Access

Create REST API endpoints for analysis queries.

**Pros:**
- Clean separation
- Works across languages

**Cons:**
- Network overhead
- Limited query flexibility
- More infrastructure

## Recommended Approach

The **packaged application** approach is recommended because:

1. **Minimal changes**: Adds capability without disrupting existing code
2. **Full access**: All models, utilities, and validators available
3. **Type safety**: IDE support and type hints work
4. **Test reuse**: Factory fixtures available for generating test data
5. **Reversible**: Easy to back out if needed

## Implementation Checklist

- [ ] Update `pyproject.toml` with package discovery configuration
- [ ] Add `setup_django()` helper to `greenweb/__init__.py`
- [ ] Create `greenweb/settings/analysis.py` minimal settings
- [ ] Add `py.typed` marker files for type hints
- [ ] Add tests for library usage
- [ ] Update README.md with library documentation
- [ ] Create example Marimo notebook
- [ ] Add CI job for library import testing
- [ ] Tag a release version for external projects to pin to

## Timeline Estimate

| Phase | Effort | Description |
|-------|--------|-------------|
| Phase 1-2 | 1-2 hours | pyproject.toml and setup helper in greenweb/__init__.py |
| Phase 3 | 1 hour | Analysis settings module |
| Phase 4-5 | 30 mins | Directory structure and type hints |
| Phase 6 | 1-2 hours | Tests |
| Phase 7 | 1-2 hours | Documentation |
| **Total** | **5-8 hours** | |

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Django version conflicts | Medium | High | Pin Django version, document requirements |
| Database credential exposure | Low | High | Use read-only credentials, document security |
| Breaking changes in models | Medium | Medium | Semantic versioning, changelog |
| Import order issues | Medium | Low | Clear documentation, helper function |

## Conclusion

Converting admin-portal to a packaged application is a low-risk, moderate-effort change that enables powerful data analysis capabilities. The main consideration is ensuring proper Django initialization and database configuration in consuming projects.

The migration can be done incrementally, and the existing deployment and test infrastructure requires no modifications.
