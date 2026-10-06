import io
import random
import unittest
from unittest.mock import patch

from PIL import Image

from image_utils import fetch_and_compress


class _Response:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass


def _noisy_png(width=1800, height=1200):
    random.seed(1)
    pixels = random.randbytes(width * height * 3)
    image = Image.frombytes('RGB', (width, height), pixels)
    output = io.BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()


class CompressionTests(unittest.TestCase):
    @patch('image_utils.requests.get')
    def test_noisy_image_obeys_budget_and_dimensions(self, get):
        get.return_value = _Response(_noisy_png())

        result = fetch_and_compress(
            'https://example.com/image.png',
            target_size_kb=40,
            max_side=640,
            preferred_quality=45,
            output_format='webp',
        )

        self.assertLessEqual(len(result.getvalue()), 40 * 1024)
        with Image.open(result) as image:
            self.assertLessEqual(max(image.size), 640)
            self.assertEqual(image.format, 'WEBP')

    @patch('image_utils.requests.get')
    def test_small_simple_image_is_not_padded_to_budget(self, get):
        image = Image.new('RGB', (320, 200), 'navy')
        source = io.BytesIO()
        image.save(source, format='PNG')
        get.return_value = _Response(source.getvalue())

        result = fetch_and_compress('https://example.com/simple.png')

        self.assertLess(len(result.getvalue()), 10 * 1024)
        with Image.open(result) as compressed:
            self.assertEqual(compressed.format, 'WEBP')

    @patch('image_utils.requests.get')
    def test_webp_preserves_transparency(self, get):
        image = Image.new('RGBA', (64, 64), (255, 0, 0, 0))
        source = io.BytesIO()
        image.save(source, format='PNG')
        get.return_value = _Response(source.getvalue())

        result = fetch_and_compress('https://example.com/transparent.png')

        with Image.open(result) as compressed:
            self.assertEqual(compressed.mode, 'RGBA')

    @patch('image_utils.requests.get')
    def test_jpeg_fallback_is_still_available(self, get):
        image = Image.new('RGB', (320, 200), 'green')
        source = io.BytesIO()
        image.save(source, format='PNG')
        get.return_value = _Response(source.getvalue())

        result = fetch_and_compress(
            'https://example.com/image.png', output_format='jpeg'
        )

        with Image.open(result) as compressed:
            self.assertEqual(compressed.format, 'JPEG')

    def test_rejects_non_http_urls(self):
        with self.assertRaises(ValueError):
            fetch_and_compress('file:///etc/passwd')


if __name__ == '__main__':
    unittest.main()
