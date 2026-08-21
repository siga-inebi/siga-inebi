from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.common.exceptions import DomainError

STUDENT_PHOTO_MAX_BYTES = 5 * 1024 * 1024
STUDENT_PHOTO_SIZE = (295, 354)


def normalize_student_photo(upload):
    """Validate and normalize one student ID photo before storage."""
    if upload.size > STUDENT_PHOTO_MAX_BYTES:
        raise DomainError("La fotografia del estudiante no puede exceder 5 MB.")

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
        raise DomainError("La fotografia del estudiante debe contener una imagen valida.") from exc

    output = BytesIO()
    normalized.save(output, format="JPEG", quality=90, optimize=True)
    if output.tell() > STUDENT_PHOTO_MAX_BYTES:
        raise DomainError("La fotografia del estudiante no pudo comprimirse por debajo de 5 MB.")

    stem = Path(getattr(upload, "name", "student-photo")).stem or "student-photo"
    return ContentFile(output.getvalue(), name=f"{stem}.jpg")
