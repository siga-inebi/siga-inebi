"""Builders of synthetic image uploads for RF-ARC-002 tests (no real photos)."""

from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import ExifTags, Image

ORIENTATION_TAG = ExifTags.Base.Orientation
GPS_IFD_TAG = ExifTags.IFD.GPSInfo


def photo_bytes(*, size=(300, 100), image_format="JPEG", orientation=None, with_gps=False):
    """Return a two-color image (red left half, blue right half) as bytes.

    ``orientation`` sets the EXIF Orientation tag and ``with_gps`` adds a GPS
    IFD with fake coordinates, mimicking what a phone camera writes.
    """
    width, height = size
    image = Image.new("RGB", size, color="blue")
    image.paste("red", (0, 0, width // 2, height))
    exif = Image.Exif()
    exif[ExifTags.Base.Make] = "Telefono de prueba"
    if orientation is not None:
        exif[ORIENTATION_TAG] = orientation
    if with_gps:
        exif[GPS_IFD_TAG] = {
            ExifTags.GPS.GPSLatitudeRef: "N",
            ExifTags.GPS.GPSLatitude: (14.0, 37.0, 0.0),
            ExifTags.GPS.GPSLongitudeRef: "W",
            ExifTags.GPS.GPSLongitude: (90.0, 31.0, 0.0),
        }
    output = BytesIO()
    image.save(output, format=image_format, exif=exif.tobytes())
    return output.getvalue()


def photo_upload(name="justificante.jpg", **kwargs):
    content_type = "image/png" if name.lower().endswith(".png") else "image/jpeg"
    if content_type == "image/png":
        kwargs.setdefault("image_format", "PNG")
    return SimpleUploadedFile(name, photo_bytes(**kwargs), content_type=content_type)
