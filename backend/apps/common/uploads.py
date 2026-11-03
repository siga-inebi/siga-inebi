"""Shared storage paths for uploaded profile photographs."""

import uuid
from pathlib import Path

from django.utils.text import slugify


def profile_photo_upload_path(*, directory, subject, owner_identifier, filename):
    """Return a meaningful, collision-resistant path without personal data."""
    safe_identifier = slugify(str(owner_identifier))[:80] or "sin-identificador"
    extension = Path(filename or "").suffix.lower() or ".jpg"
    unique_suffix = uuid.uuid4().hex[:12]
    return f"{directory}/foto_{subject}_{safe_identifier}_{unique_suffix}{extension}"
