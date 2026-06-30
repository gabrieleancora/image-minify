import re
import requests
from flask import Blueprint, request, send_file, url_for
from image_utils import fetch_and_compress

bp = Blueprint('x_minify', __name__)

_FXTWITTER_API = 'https://api.fxtwitter.com/2/status/{}'
_STATUS_ID_RE = re.compile(r'/status/(\d+)')


@bp.route('/')
def index():
    return 'Hello x_minify!'


@bp.route('/minify')
def show_x_images():
    url = request.args.get('url')
    match = _STATUS_ID_RE.search(url)
    if not match:
        return 'Could not extract status ID from URL', 400

    status_id = match.group(1)
    api_resp = requests.get(_FXTWITTER_API.format(status_id), timeout=10)
    api_resp.raise_for_status()

    photos = api_resp.json().get('status', {}).get('media', {}).get('photos', [])
    if not photos:
        return 'No photos found in this tweet', 404

    imgs = ''.join(
        f'<img src="{url_for("x_minify.serve_compressed_image", url=p["url"])}" alt="X Image">'
        for p in photos
    )
    return imgs


@bp.route('/image')
def serve_compressed_image():
    url = request.args.get('url')
    buf = fetch_and_compress(url)
    return send_file(buf, mimetype='image/jpeg')
