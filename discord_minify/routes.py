from flask import Blueprint, request, send_file, url_for
from image_utils import fetch_and_compress

bp = Blueprint('discord_minify', __name__)


@bp.route('/')
def index():
    return 'Hello discord_minify!'


@bp.route('/minify')
def show_discord_image():
    url = request.args.get('url')
    print(f'Requested image {url}')
    image_url = url_for('discord_minify.serve_compressed_image', url=url)
    return f'<img src="{image_url}" alt="Discord Image">'


@bp.route('/image')
def serve_compressed_image():
    url = request.args.get('url')
    buf = fetch_and_compress(url)
    return send_file(buf, mimetype='image/jpeg')