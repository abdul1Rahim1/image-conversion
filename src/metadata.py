"""Strip original EXIF and inject fresh randomized metadata."""

import io
import random
from datetime import datetime, timedelta

import piexif
from PIL import Image


CAMERA_MAKES = [
    ("Canon", "EOS R6 Mark II"),
    ("Canon", "EOS 5D Mark IV"),
    ("Nikon", "Z 7II"),
    ("Nikon", "D850"),
    ("Sony", "ILCE-7M4"),
    ("Sony", "ILCE-1"),
    ("FUJIFILM", "X-T5"),
    ("Panasonic", "DC-S5M2"),
]

LENSES = [
    "50mm f/1.8",
    "24-70mm f/2.8",
    "85mm f/1.4",
    "35mm f/1.4",
    "100mm f/2.8 Macro",
    "70-200mm f/2.8",
]

SOFTWARE = [
    "Adobe Photoshop 25.0",
    "Capture One 23",
    "Lightroom Classic 13.1",
    "Affinity Photo 2.3",
]


def _random_datetime_within_days(days: int = 180) -> str:
    now = datetime.now()
    delta = timedelta(
        days=random.randint(0, days),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    return (now - delta).strftime("%Y:%m:%d %H:%M:%S")


def scrub_and_randomize(
    image_bytes: bytes,
    output_format: str = "webp",
    quality: int = 85,
) -> bytes:
    """Re-encode image, wiping the original EXIF, then inject fresh fake EXIF.

    Note: WebP preserves EXIF but not the full set of legacy tags — that's
    fine, the goal is: no original metadata + plausible new metadata.
    """
    src = Image.open(io.BytesIO(image_bytes))
    if src.mode not in ("RGB", "RGBA"):
        src = src.convert("RGB")

    # First pass: re-encode into a scratch buffer with NO exif
    scratch = io.BytesIO()
    save_kwargs = {"quality": quality}
    if output_format == "webp":
        save_kwargs["method"] = 6
    src.save(scratch, format=output_format.upper(), **save_kwargs)
    scratch.seek(0)

    # Build fake EXIF
    make, model = random.choice(CAMERA_MAKES)
    lens = random.choice(LENSES)
    software = random.choice(SOFTWARE)
    dt = _random_datetime_within_days()

    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: make.encode(),
            piexif.ImageIFD.Model: model.encode(),
            piexif.ImageIFD.Software: software.encode(),
            piexif.ImageIFD.DateTime: dt.encode(),
            piexif.ImageIFD.Artist: b"",
            piexif.ImageIFD.Copyright: b"",
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: dt.encode(),
            piexif.ExifIFD.DateTimeDigitized: dt.encode(),
            piexif.ExifIFD.LensModel: lens.encode(),
            piexif.ExifIFD.FNumber: (random.choice([14, 18, 28, 40, 56, 80]), 10),
            piexif.ExifIFD.ExposureTime: (1, random.choice([60, 125, 200, 400, 800])),
            piexif.ExifIFD.ISOSpeedRatings: random.choice([100, 200, 400, 800]),
            piexif.ExifIFD.FocalLength: (random.choice([35, 50, 85, 100]), 1),
        },
        "GPS": {},
        "1st": {},
        "thumbnail": None,
    }

    try:
        exif_bytes = piexif.dump(exif_dict)
    except Exception:
        # If piexif can't produce it for some reason, return scrubbed image
        return scratch.getvalue()

    # Second pass: reopen scratch and re-save with the fake exif attached
    reopened = Image.open(scratch)
    if reopened.mode not in ("RGB", "RGBA"):
        reopened = reopened.convert("RGB")
    final = io.BytesIO()
    reopened.save(final, format=output_format.upper(), exif=exif_bytes, **save_kwargs)
    return final.getvalue()
