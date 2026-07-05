import re
import requests
from flask import Blueprint, request, send_file, url_for
from image_utils import fetch_and_compress

bp = Blueprint('minify', __name__)

_FXTWITTER_API = 'https://api.fxtwitter.com/2/status/{}'
_X_STATUS_ID_RE = re.compile(r'/status/(\d+)')
_X_HOSTS = {'x.com', 'twitter.com', 'www.x.com', 'www.twitter.com', 'fxtwitter.com', 'www.fxtwitter.com'}


def _is_x_url(url: str) -> bool:
    from urllib.parse import urlparse
    return urlparse(url).hostname in _X_HOSTS


def _get_url_param() -> str | None:
    from urllib.parse import unquote
    raw = request.query_string.decode('utf-8')
    prefix = 'url='
    idx = raw.find(prefix)
    if idx == -1:
        return None
    return unquote(raw[idx + len(prefix):])


@bp.route('/minify')
def minify():
    url = _get_url_param()
    if not url:
        return 'Missing url parameter', 400

    if _is_x_url(url):
        return _minify_x(url)
    return _minify_direct(url)


def _minify_direct(url: str) -> str:
    image_url = url_for('minify.serve_compressed_image', url=url)
    return f'<img src="{image_url}" alt="Small image">'


def _minify_x(url: str) -> str:
    match = _X_STATUS_ID_RE.search(url)
    if not match:
        return 'Could not extract status ID from URL', 400

    status_id = match.group(1)
    api_resp = requests.get(_FXTWITTER_API.format(status_id), timeout=10)
    api_resp.raise_for_status()

    photos = api_resp.json().get('status', {}).get('media', {}).get('photos', [])
    if not photos:
        return 'No photos found in this tweet', 404

    return ''.join(
        f'<img src="{url_for("minify.serve_compressed_image", url=p["url"])}" alt="X Image">'
        for p in photos
    )


@bp.route('/image')
def serve_compressed_image():
    url = _get_url_param()
    buf = fetch_and_compress(url)
    return send_file(buf, mimetype='image/jpeg')
