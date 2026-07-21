# Image-Minify

A small web server that turns direct image URLs and X/Twitter status URLs into
bandwidth-friendly images for airplane messaging Wi-Fi and other very slow links.

## Usage

Start the server:

```powershell
python main.py
```

Then open (URL-encode the source URL when constructing this programmatically):

```text
http://127.0.0.1:5000/minify?url=https://example.com/photo.jpg
```

Three compression modes are available:

| Mode | Maximum transfer size per image | Maximum side | Preferred quality |
| --- | ---: | ---: | ---: |
| `data` | 40 KB | 640 px | 45 |
| `balanced` (default) | 100 KB | 1200 px | 65 |
| `detail` | 250 KB | 1920 px | 80 |

For example:

```text
http://127.0.0.1:5000/minify?mode=data&url=https://example.com/photo.jpg
```

If `token.txt` contains a token, add `token=...` before `url`. Keep `url` as the
last query parameter when pasting a URL without encoding it so that source URLs
containing their own `&` parameters (such as Discord CDN URLs) remain intact.

The maximum transfer size is a ceiling rather than a target. The compressor
first uses the preferred quality, keeping the result as-is when it is already
under the limit. It only lowers quality and dimensions when necessary.

WebP is served to Safari 14+ and other modern browsers. The generated page uses
JPEG as an automatic fallback for older browsers. WebP also preserves image
transparency; the JPEG fallback places transparent images on a white background.
