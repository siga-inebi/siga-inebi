from io import BytesIO

import pytest
from PIL import Image

from apps.common.exceptions import DomainError
from apps.common.images import normalize_image_payload
from tests.factories.images import GPS_IFD_TAG, ORIENTATION_TAG, photo_bytes

pytestmark = [pytest.mark.unit]


def _open(payload):
    image = Image.open(BytesIO(payload))
    image.load()
    return image


def test_normalize_image_payload_caps_the_longest_side(settings):
    """RF-ARC-002: una imagen grande se reduce al lado maximo configurado y pesa menos."""
    settings.IMAGE_UPLOAD_MAX_DIMENSION_PX = 512
    original = photo_bytes(size=(3000, 1500))

    normalized = normalize_image_payload(original, content_type="image/jpeg")

    image = _open(normalized)
    assert image.format == "JPEG"
    assert image.size == (512, 256)
    assert len(normalized) < len(original)


def test_normalize_image_payload_keeps_small_images_at_their_size(settings):
    """RF-ARC-002: el limite solo reduce; una imagen pequena no se amplia."""
    settings.IMAGE_UPLOAD_MAX_DIMENSION_PX = 512

    normalized = normalize_image_payload(photo_bytes(size=(200, 80)), content_type="image/jpeg")

    assert _open(normalized).size == (200, 80)


@pytest.mark.parametrize(
    ("image_format", "content_type"), [("JPEG", "image/jpeg"), ("PNG", "image/png")]
)
def test_normalize_image_payload_strips_exif_and_gps(image_format, content_type):
    """RF-ARC-002: se eliminan EXIF y GPS (privacidad de menores) en JPEG y PNG."""
    original = photo_bytes(image_format=image_format, with_gps=True)
    assert _open(original).getexif().get_ifd(GPS_IFD_TAG)

    normalized = normalize_image_payload(original, content_type=content_type)

    image = _open(normalized)
    assert image.format == image_format
    assert dict(image.getexif()) == {}
    assert "exif" not in image.info
    assert b"Telefono de prueba" not in normalized


def test_normalize_image_payload_applies_the_exif_orientation():
    """RF-ARC-002: la orientacion EXIF se aplica a los pixeles antes de descartarla."""
    # Orientation 6 = rotar 90 grados en sentido horario: la mitad izquierda
    # (roja) del sensor queda arriba en la imagen que ve el usuario.
    original = photo_bytes(size=(300, 100), orientation=6)

    image = _open(normalize_image_payload(original, content_type="image/jpeg"))

    assert image.size == (100, 300)
    assert ORIENTATION_TAG not in image.getexif()
    red, green, blue = image.getpixel((50, 20))
    assert red > 200 and blue < 60
    red, green, blue = image.getpixel((50, 280))
    assert blue > 200 and red < 60


def test_normalize_image_payload_leaves_pdf_untouched():
    """RF-ARC-002: los PDF y demas no-imagenes pasan sin cambios."""
    pdf = b"%PDF-1.4 contenido de prueba"

    assert normalize_image_payload(pdf, content_type="application/pdf") is pdf


def test_normalize_image_payload_rejects_a_corrupt_image():
    """RF-ARC-002: una imagen danada se rechaza con un error de validacion en espanol."""
    corrupt = photo_bytes()[:200]

    with pytest.raises(DomainError, match="La imagen adjunta esta danada"):
        normalize_image_payload(corrupt, content_type="image/jpeg")
