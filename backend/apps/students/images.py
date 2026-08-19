from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.common.models import DomainError

STUDENT_PHOTO_MAX_BYTES = 5 * 1024 * 1024
STUDENT_PHOTO_SIZE = (295, 354)


def normalize_student_photo(upload):
    """Validate and normalize one student ID photo before storage."""
    if upload.size > STUDENT_PHOTO_MAX_BYTES:
        raise DomainError("Student photo cannot exceed 5 MB.")

    try:
        upload.seek(0)
        with Image.open(upload) as source:
            source.load()
            normalized = ImageOps.fit(
                ImageOps.exif_transpose(source).convert("RGB"),
                STUDENT_PHOTO_SIZE,
                method=Image.Resampling.LANCZOS,
            )
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise DomainError("Student photo must contain a valid image.") from exc

    output = BytesIO()
    normalized.save(output, format="JPEG", quality=90, optimize=True)
    if output.tell() > STUDENT_PHOTO_MAX_BYTES:
        raise DomainError("Student photo could not be compressed below 5 MB.")

    stem = Path(getattr(upload, "name", "student-photo")).stem or "student-photo"
    return ContentFile(output.getvalue(), name=f"{stem}.jpg")
