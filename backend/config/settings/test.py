# ruff: noqa: F403,F405
from django.core.exceptions import ImproperlyConfigured

from .base import *

if DATABASE_ENGINE != "postgresql":
    raise ImproperlyConfigured("Test settings require DATABASE_ENGINE=postgresql.")

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
