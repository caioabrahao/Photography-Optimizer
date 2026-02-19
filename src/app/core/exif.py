from __future__ import annotations

from fractions import Fraction
from typing import Any

from PIL import ExifTags, Image


TAGS = ExifTags.TAGS


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        denominator = getattr(value, "denominator", 0)
        if denominator:
            return float(value)
        return None
    if isinstance(value, tuple) and len(value) == 2 and value[1] != 0:
        return float(value[0]) / float(value[1])
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _format_fraction(value: Any) -> str | None:
    number = _to_float(value)
    if number is None or number <= 0:
        return None
    if number < 1:
        try:
            fraction = Fraction(number).limit_denominator(8000)
            return f"{fraction.numerator}/{fraction.denominator}"
        except (ValueError, ZeroDivisionError):
            return f"{number:.6f}"
    return f"{number:.4f}".rstrip("0").rstrip(".")


def _tag_map(exif: dict[int, Any]) -> dict[str, Any]:
    mapped: dict[str, Any] = {}
    for tag_id, value in exif.items():
        mapped[TAGS.get(tag_id, str(tag_id))] = value
    return mapped


def extract_exif_data(image: Image.Image) -> dict[str, Any]:
    raw_exif = image.getexif()
    exif_by_name = _tag_map(dict(raw_exif.items())) if raw_exif else {}

    if raw_exif and hasattr(raw_exif, "get_ifd"):
        try:
            exif_ifd = raw_exif.get_ifd(ExifTags.IFD.Exif)
            if exif_ifd:
                exif_by_name.update(_tag_map(dict(exif_ifd.items())))
        except Exception:
            pass

    iso = exif_by_name.get("ISOSpeedRatings") or exif_by_name.get("PhotographicSensitivity")
    exposure_time = exif_by_name.get("ExposureTime")
    f_number = exif_by_name.get("FNumber")
    focal_length = exif_by_name.get("FocalLength")

    aperture_float = _to_float(f_number)
    focal_length_float = _to_float(focal_length)

    data: dict[str, Any] = {
        "iso": iso,
        "shutter_speed": _format_fraction(exposure_time),
        "aperture": f"f/{aperture_float:.1f}" if aperture_float else None,
        "camera_model": exif_by_name.get("Model"),
        "camera_make": exif_by_name.get("Make"),
        "lens": exif_by_name.get("LensModel"),
        "focal_length": f"{focal_length_float:.0f}mm" if focal_length_float else None,
        "datetime_original": exif_by_name.get("DateTimeOriginal"),
        "software": exif_by_name.get("Software"),
        "artist": exif_by_name.get("Artist"),
        "image_width": image.width,
        "image_height": image.height,
    }

    cleaned = {key: value for key, value in data.items() if value not in (None, "")}
    return cleaned
