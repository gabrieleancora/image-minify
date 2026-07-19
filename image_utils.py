import io
import math
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps


DEFAULT_TARGET_SIZE_KB = 100
DEFAULT_MAX_SIDE = 1200
_MIN_JPEG_QUALITY = 10
_MAX_JPEG_QUALITY = 85
_MIN_SIDE = 64


def _encode_jpeg(img: Image.Image, quality: int) -> io.BytesIO:
    buf = io.BytesIO()
    img.save(
        buf,
        format='JPEG',
        quality=quality,
        optimize=True,
        progressive=True,
        subsampling=2,
    )
    return buf


def _fit_to_budget(img: Image.Image, target_bytes: int) -> io.BytesIO:
    """Return the highest-quality JPEG we can make within target_bytes."""
    full_quality = _encode_jpeg(img, _MAX_JPEG_QUALITY)
    if full_quality.tell() <= target_bytes:
        full_quality.seek(0)
        return full_quality

    # Quality alone is not enough for noisy photos. Keep reducing resolution
    # until even the minimum useful JPEG quality fits the requested budget.
    while True:
        minimum_quality = _encode_jpeg(img, _MIN_JPEG_QUALITY)
        if minimum_quality.tell() <= target_bytes:
            break

        if max(img.size) <= _MIN_SIDE:
            minimum_quality.seek(0)
            return minimum_quality

        estimated_scale = math.sqrt(target_bytes / minimum_quality.tell()) * 0.95
        scale = min(0.85, max(0.25, estimated_scale))
        new_size = (
            max(1, round(img.width * scale)),
            max(1, round(img.height * scale)),
        )
        if new_size == img.size:
            minimum_quality.seek(0)
            return minimum_quality
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    # Find the best quality in a handful of encodes instead of stepping down
    # through every quality level.
    best = minimum_quality
    low, high = _MIN_JPEG_QUALITY + 1, _MAX_JPEG_QUALITY - 1
    while low <= high:
        quality = (low + high) // 2
        candidate = _encode_jpeg(img, quality)
        if candidate.tell() <= target_bytes:
            best = candidate
            low = quality + 1
        else:
            high = quality - 1

    best.seek(0)
    return best


def fetch_and_compress(
    url: str,
    target_size_kb: int = DEFAULT_TARGET_SIZE_KB,
    max_side: int = DEFAULT_MAX_SIDE,
) -> io.BytesIO:
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError('Only http:// and https:// image URLs are supported')

    response = requests.get(url, timeout=(5, 20))
    response.raise_for_status()

    with Image.open(io.BytesIO(response.content)) as source:
        img = ImageOps.exif_transpose(source)
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

        # JPEG has no transparency. A white background is more useful than the
        # black background produced by a direct RGBA-to-RGB conversion.
        if img.mode in ('RGBA', 'LA') or (
            img.mode == 'P' and 'transparency' in img.info
        ):
            rgba = img.convert('RGBA')
            background = Image.new('RGB', rgba.size, 'white')
            background.paste(rgba, mask=rgba.getchannel('A'))
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        return _fit_to_budget(img, target_size_kb * 1024)
