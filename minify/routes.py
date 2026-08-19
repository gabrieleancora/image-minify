import html
import hmac
import os
import re
import requests
from PIL import Image
from flask import Blueprint, request, send_file, url_for
from image_utils import fetch_and_compress

bp = Blueprint('minify', __name__)

_FXTWITTER_API = 'https://api.fxtwitter.com/2/status/{}'
_X_STATUS_ID_RE = re.compile(r'/status/(\d+)')
_X_HOSTS = {'x.com', 'twitter.com', 'www.x.com', 'www.twitter.com', 'fxtwitter.com', 'www.fxtwitter.com'}
_PRESETS = {
    # Maximum KB, maximum side in pixels, preferred quality. The byte size is
    # a ceiling, not a target: images that compress well remain much smaller.
    'data': (40, 640, 45),
    'balanced': (100, 1200, 65),
    'detail': (250, 1920, 80),
}
_OUTPUT_FORMATS = {'webp': 'image/webp', 'jpeg': 'image/jpeg'}
_TOKEN_ENV_VAR = 'PLANE_WIFI_TOKEN'


def _get_token():
    return request.args.get('token')


_TOKEN_FILE = os.path.join(os.path.dirname(__file__), '..', 'token.txt')
_cached_token = None
_token_loaded = False


def _load_token():
    global _cached_token, _token_loaded

    if _token_loaded:
        return _cached_token

    environment_token = os.getenv(_TOKEN_ENV_VAR, '').strip()
    if environment_token:
        _cached_token = environment_token
    else:
        try:
            with open(_TOKEN_FILE) as f:
                _cached_token = f.read().strip()
        except FileNotFoundError:
            _cached_token = None

    _token_loaded = True
    return _cached_token


def _check_token():
    expected = _load_token()
    if not expected:
        return True  # no token file → open access
    provided = _get_token()
    if not provided:
        return False
    return hmac.compare_digest(provided, expected)


def _get_url_param():
    from urllib.parse import unquote
    raw = request.query_string.decode('utf-8')
    idx = raw.find('url=')
    if idx == -1:
        return None
    return unquote(raw[idx + 4:])


def _get_preset():
    return request.args.get('mode', 'balanced')


def _image_url(url: str, output_format: str):
    return url_for(
        'minify.serve_compressed_image',
        token=_get_token(),
        mode=_get_preset(),
        format=output_format,
        url=url,
    )


def _image_tag(url: str, alt: str):
    webp_url = html.escape(_image_url(url, 'webp'), quote=True)
    jpeg_url = html.escape(_image_url(url, 'jpeg'), quote=True)
    escaped_alt = html.escape(alt, quote=True)
    return (
        f'<picture><source srcset="{webp_url}" type="image/webp">'
        f'<img src="{jpeg_url}" alt="{escaped_alt}"></picture>'
    )


@bp.route('/minify')
def minify():
    if not _check_token():
        return 'Unauthorized', 401

    url = _get_url_param()
    if not url:
        return 'Missing url parameter', 400

    if _get_preset() not in _PRESETS:
        return 'Invalid mode; use data, balanced, or detail', 400

    if _is_x_url(url):
        return _minify_x(url)
    return _minify_direct(url)


def _is_x_url(url: str):
    from urllib.parse import urlparse
    return urlparse(url).hostname in _X_HOSTS


def _minify_direct(url: str):
    return _image_tag(url, 'Small image')


def _minify_x(url: str):
    match = _X_STATUS_ID_RE.search(url)
    if not match:
        return 'Could not extract status ID from URL', 400

    status_id = match.group(1)
    try:
        api_resp = requests.get(_FXTWITTER_API.format(status_id), timeout=(5, 10))
        api_resp.raise_for_status()
        photos = api_resp.json().get('status', {}).get('media', {}).get('photos', [])
    except (requests.RequestException, ValueError):
        return 'Could not retrieve this X post', 502
    if not photos:
        return 'No photos found in this tweet', 404

    return ''.join(
        _image_tag(photo['url'], 'X Image')
        for photo in photos
        if photo.get('url')
    )


@bp.route('/image')
def serve_compressed_image():
    if not _check_token():
        return 'Unauthorized', 401

    url = _get_url_param()
    if not url:
        return 'Missing url parameter', 400

    preset = _PRESETS.get(_get_preset())
    if preset is None:
        return 'Invalid mode; use data, balanced, or detail', 400

    output_format = request.args.get('format', 'webp').lower()
    mimetype = _OUTPUT_FORMATS.get(output_format)
    if mimetype is None:
        return 'Invalid format; use webp or jpeg', 400

    target_size_kb, max_side, preferred_quality = preset
    try:
        buf = fetch_and_compress(
            url,
            target_size_kb,
            max_side,
            preferred_quality,
            output_format,
        )
    except ValueError as exc:
        return str(exc), 400
    except requests.RequestException:
        return 'Could not download the source image', 502
    except (Image.UnidentifiedImageError, Image.DecompressionBombError, OSError):
        return 'The URL did not return a supported image', 415

    response = send_file(buf, mimetype=mimetype, max_age=86400)
    response.cache_control.private = True
    response.cache_control.public = False
    return response
