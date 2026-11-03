from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

from apps.common.exceptions import DomainError
from apps.common.images import open_oriented_image

STUDENT_PHOTO_MAX_BYTES = 5 * 1024 * 1024
STUDENT_PHOTO_SIZE = (295, 354)


def normalize_student_photo(upload):
    """Validate and normalize one student ID photo before storage.

    Decoding, EXIF orientation and metadata removal are shared with every other
    image upload (``apps.common.images``, RF-ARC-002); the ID crop is specific.
    """
    if upload.size > STUDENT_PHOTO_MAX_BYTES:
        raise DomainError("La fotografia del estudiante no puede exceder 5 MB.")

    source = open_oriented_image(
        upload, error_message="La fotografia del estudiante debe contener una imagen valida."
    )
    normalized = ImageOps.fit(
        source.convert("RGB"),
        STUDENT_PHOTO_SIZE,
        method=Image.Resampling.LANCZOS,
    )

    output = BytesIO()
    normalized.save(output, format="JPEG", quality=90, optimize=True)
    if output.tell() > STUDENT_PHOTO_MAX_BYTES:
        raise DomainError("La fotografia del estudiante no pudo comprimirse por debajo de 5 MB.")

    stem = Path(getattr(upload, "name", "student-photo")).stem or "student-photo"
    return ContentFile(output.getvalue(), name=f"{stem}.jpg")
