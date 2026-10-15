"""
Shared image normalization for every upload that may carry a photograph.

RF-ARC-002 asks the system to compress and normalize attached images before
storage. The Pillow mechanics live here once so the student ID photo
(``apps.students.images``) and the attachment uploads (``apps.documents`` and
the attendance justifications that reuse its validation) apply the same rules:

- the EXIF orientation is applied to the pixels, so the stored image looks the
  same without depending on metadata;
- every metadata block (EXIF, GPS, comments, XMP) is dropped. Uploads come from
  phones of guardians of minors and GPS coordinates must not reach storage;
- the longest side is capped and the result is re-encoded in its declared
  format (JPEG with a bounded quality, PNG with lossless optimization);
- an unreadable image is rejected with a ``DomainError`` in Spanish.

Limits come from ``settings`` (environment variables), following the operational
parameters pattern documented in ``docs/architecture/configuration-catalogues.md``.
"""

from io import BytesIO

from django.conf import settings
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.common.exceptions import DomainError

DEFAULT_IMAGE_MAX_DIMENSION_PX = 2048
DEFAULT_IMAGE_JPEG_QUALITY = 85

# Declared content type -> Pillow encoder. The declared type wins over the real
# one so the stored extension, ``content_type`` and bytes always agree.
NORMALIZED_IMAGE_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
}

_PNG_MODES = {"1", "L", "LA", "I", "I;16", "P", "RGB", "RGBA"}
_JPEG_MODES = {"L", "RGB"}
_RENDERING_INFO_KEYS = ("transparency", "icc_profile")
_UNREADABLE_IMAGE_ERRORS = (
    Image.DecompressionBombError,
    UnidentifiedImageError,
    OSError,
    ValueError,
    SyntaxError,
)


def open_oriented_image(source, *, error_message):
    """Decode ``source`` (file-like) fully and return it upright, without metadata.

    Raises ``DomainError(error_message)`` when the bytes are not a readable image.
    """
    try:
        if hasattr(source, "seek"):
            source.seek(0)
        with Image.open(source) as opened:
            opened.load()
            oriented = ImageOps.exif_transpose(opened)
            if oriented is opened:
                oriented = opened.copy()
    except _UNREADABLE_IMAGE_ERRORS as exc:
        raise DomainError(error_message) from exc
    # Drop EXIF/GPS, XMP, comments and text chunks; keep only what is needed to
    # render the pixels the same way (palette transparency and color profile).
    oriented.info = {
        key: oriented.info[key] for key in _RENDERING_INFO_KEYS if key in oriented.info
    }
    return oriented


def image_max_dimension():
    return getattr(settings, "IMAGE_UPLOAD_MAX_DIMENSION_PX", DEFAULT_IMAGE_MAX_DIMENSION_PX)


def image_jpeg_quality():
    return getattr(settings, "IMAGE_UPLOAD_JPEG_QUALITY", DEFAULT_IMAGE_JPEG_QUALITY)


def normalize_image_payload(payload, *, content_type):
    """Return the bytes to store for an upload declared as ``content_type``.

    Images (``NORMALIZED_IMAGE_FORMATS``) come back upright, without metadata,
    with the longest side capped and re-encoded. Anything else (PDF, ...) is
    returned unchanged.
    """
    image_format = NORMALIZED_IMAGE_FORMATS.get((content_type or "").lower())
    if image_format is None:
        return payload

    image = open_oriented_image(
        BytesIO(payload),
        error_message="La imagen adjunta esta danada o no es una imagen valida.",
    )
    max_dimension = image_max_dimension()
    image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    supported_modes = _JPEG_MODES if image_format == "JPEG" else _PNG_MODES
    options = {"optimize": True}
    if image.mode in supported_modes:
        # The color profile only describes the pixels it came with.
        if "icc_profile" in image.info:
            options["icc_profile"] = image.info["icc_profile"]
    elif image_format == "JPEG":
        image = image.convert("RGBA").convert("RGB") if image.mode == "P" else image.convert("RGB")
    else:
        image = image.convert("RGBA")
    if image_format == "JPEG":
        options["quality"] = image_jpeg_quality()

    output = BytesIO()
    image.save(output, format=image_format, **options)
    return output.getvalue()
