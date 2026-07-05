import io
import requests
from PIL import Image

_TARGET_SIZE_KB = 100
_MAX_SIDE = 1200


def fetch_and_compress(url: str) -> io.BytesIO:
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    img = Image.open(io.BytesIO(response.content))
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    if max(img.width, img.height) > _MAX_SIDE:
        img.thumbnail((_MAX_SIDE, _MAX_SIDE), Image.LANCZOS)

    quality = 85
    while quality >= 10:
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        if buf.tell() <= _TARGET_SIZE_KB * 1024:
            break
        quality -= 10

    buf.seek(0)
    return buf
