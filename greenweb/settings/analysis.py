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

# Minimal middleware - none needed for analysis
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
