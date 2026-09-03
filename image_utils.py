import io
import math
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps

# Configuration constants for image processing
DEFAULT_TARGET_SIZE_KB = 100
DEFAULT_MAX_SIDE = 1200
DEFAULT_QUALITY = 65
_MIN_QUALITY = 10
_MIN_SIDE = 64
_OUTPUT_FORMATS = {'jpeg', 'webp'}


def _encode_image(
        img: Image.Image,
        quality: int,
        output_format: str,
) -> io.BytesIO:
    """Encodes an Image object into a BytesIO buffer with specified quality and format."""
    buf = io.BytesIO()
    if output_format == 'webp':
        # Use webp specific encoding with method 4 for better compression
        img.save(buf, format='WEBP', quality=quality, method=4)
    else:
        # Use jpeg encoding with optimization and progressive features
        img.save(
            buf,
            format='JPEG',
            quality=quality,
            optimize=True,
            progressive=True,
            subsampling=2,
        )
    return buf


def _fit_to_budget(
        img: Image.Image,
        target_bytes: int,
        preferred_quality: int,
        output_format: str,
) -> io.BytesIO:
    """Compress at preferred quality, treating target_bytes as a hard ceiling."""
    # Try encoding with the preferred quality first
    preferred = _encode_image(img, preferred_quality, output_format)
    if preferred.tell() <= target_bytes:
        preferred.seek(0)
        return preferred

    # Quality alone is not always enough for noisy images. Reduce resolution
    # until the minimum useful quality fits the requested budget.
    while True:
        # Check if the image fits the budget at minimum quality
        minimum_quality = _encode_image(img, _MIN_QUALITY, output_format)
        if minimum_quality.tell() <= target_bytes:
            break

        # If even the minimum quality is too large, and we are at minimum side, stop
        if max(img.size) <= _MIN_SIDE:
            minimum_quality.seek(0)
            return minimum_quality

        # Calculate a scale factor based on the current size vs target budget
        estimated_scale = math.sqrt(target_bytes / minimum_quality.tell()) * 0.95
        scale = min(0.85, max(0.25, estimated_scale))
        new_size = (
            max(1, round(img.width * scale)),
            max(1, round(img.height * scale)),
        )

        # If resizing doesn't change the dimensions, return current best
        if new_size == img.size:
            minimum_quality.seek(0)
            return minimum_quality

        # Resize the image and repeat the loop to check quality again
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    # Find the best quality no higher than the preset's preferred quality.
    # Uses a binary search approach to find the highest quality that fits the budget.
    best = minimum_quality
    low, high = _MIN_QUALITY + 1, preferred_quality - 1
    while low <= high:
        quality = (low + high) // 2
        candidate = _encode_image(img, quality, output_format)
        if candidate.tell() <= target_bytes:
            best = candidate
            low = quality + 1
        else:
            high = quality - 1

    best.seek(0)
    return best


def _prepare_image(img: Image.Image, output_format: str) -> Image.Image:
    """Prepares image by handling alpha channels and converting to appropriate color modes."""
    # Check if the image has transparency/alpha channel
    has_alpha = img.mode in ('RGBA', 'LA') or (
            img.mode == 'P' and 'transparency' in img.info
    )

    # Special handling for WebP with transparency
    if output_format == 'webp' and has_alpha:
        return img.convert('RGBA')

    # For other formats, flatten images with alpha onto a white background
    if has_alpha:
        rgba = img.convert('RGBA')
        background = Image.new('RGB', rgba.size, 'white')
        background.paste(rgba, mask=rgba.getchannel('A'))
        return background

    # Ensure the image is in RGB mode if it's not already (e.g., grayscale, etc.)
    if img.mode != 'RGB':
        return img.convert('RGB')
    return img


def fetch_and_compress(
        url: str,
        target_size_kb: int = DEFAULT_TARGET_SIZE_KB,
        max_side: int = DEFAULT_MAX_SIDE,
        preferred_quality: int = DEFAULT_QUALITY,
        output_format: str = 'webp',
) -> io.BytesIO:
    """Fetches an image from a URL and returns a compressed version in BytesIO."""
    output_format = output_format.lower()
    # Validate the requested output format
    if output_format not in _OUTPUT_FORMATS:
        raise ValueError('Output format must be webp or jpeg')

    # Validate the URL scheme
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError('Only http:// and https:// image URLs are supported')

    # Fetch the image content from the internet
    response = requests.get(url, timeout=(5, 20))
    response.raise_for_status()

    # Process the image content
    with Image.open(io.BytesIO(response.content)) as source:
        # Correct orientation based on EXIF data
        img = ImageOps.exif_transpose(source)
        # Resize image to fit within the max side constraint
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        # Prepare colors and alpha
        img = _prepare_image(img, output_format)
        # Compress to meet the target size budget
        return _fit_to_budget(
            img,
            target_size_kb * 1024,
            preferred_quality,
            output_format,
        )