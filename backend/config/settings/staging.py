# ruff: noqa: F403,F405
from django.core.exceptions import ImproperlyConfigured

from .base import *

require_postgresql()

DEBUG = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

if SECRET_KEY == "insecure-development-key":
    raise ImproperlyConfigured("Staging requires DJANGO_SECRET_KEY.")

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Staging requires DJANGO_ALLOWED_HOSTS.")
