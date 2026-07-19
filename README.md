# Image-Minify

A small web server that turns direct image URLs and X/Twitter status URLs into
bandwidth-friendly JPEGs for airplane messaging Wi-Fi and other very slow links.

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

| Mode | Maximum transfer size per image | Maximum side |
| --- | ---: | ---: |
| `data` | 40 KB | 640 px |
| `balanced` (default) | 100 KB | 1200 px |
| `detail` | 250 KB | 1920 px |

For example:

```text
http://127.0.0.1:5000/minify?mode=data&url=https://example.com/photo.jpg
```

If `token.txt` contains a token, add `token=...` before `url`. Keep `url` as the
last query parameter when pasting a URL without encoding it so that source URLs
containing their own `&` parameters (such as Discord CDN URLs) remain intact.

The compressor preserves orientation, puts transparent images on a white
background, and reduces both JPEG quality and pixel dimensions when necessary
to stay inside the selected byte budget.
