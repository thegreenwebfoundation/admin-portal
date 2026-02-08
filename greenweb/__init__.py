"""Setup helper for using admin-portal as a library."""
import os


def setup_django(
    settings_module: str = "greenweb.settings.analysis",
    database_url: str | None = None,
):
    """
    Configure Django for library/notebook usage.

    Call this before importing any Django models.

    Args:
        settings_module: Django settings module path. Defaults to analysis settings.
        database_url: Database connection URL. If not provided, reads from DATABASE_URL env var.

    Example:
        >>> import os
        >>> os.environ["DATABASE_URL"] = "mysql://user:pass@localhost/greencheck"
        >>> from greenweb import setup_django
        >>> setup_django()
        >>> from apps.greencheck.models import GreenDomain
    """
    import django

    if database_url:
        os.environ["DATABASE_URL"] = database_url

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

    # Set DJANGO_ALLOW_ASYNC_UNSAFE for notebook environments
    os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "True")

    if not django.apps.apps.ready:
        django.setup()
