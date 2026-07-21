import io
import unittest
from unittest.mock import patch

from app import start_app


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.client = start_app().test_client()

    @patch('minify.routes._check_token', return_value=True)
    def test_mode_is_forwarded_and_nested_query_is_preserved(self, _check_token):
        response = self.client.get(
            '/minify',
            query_string={
                'mode': 'data',
                'url': 'https://cdn.example/image.png?width=100&key=abc',
            },
        )

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('mode=data', body)
        self.assertIn('width%3D100%26key%3Dabc', body)
        self.assertIn('<picture>', body)
        self.assertIn('format=webp', body)
        self.assertIn('format=jpeg', body)

    @patch('minify.routes._check_token', return_value=True)
    def test_invalid_mode_is_rejected(self, _check_token):
        response = self.client.get(
            '/minify?mode=unlimited&url=https://example.com/image.jpg'
        )
        self.assertEqual(response.status_code, 400)

    @patch('minify.routes.fetch_and_compress')
    @patch('minify.routes._check_token', return_value=True)
    def test_image_response_is_privately_cacheable(self, _check_token, compress):
        compress.return_value = io.BytesIO(b'webp data')

        response = self.client.get(
            '/image?mode=data&url=https://example.com/image.jpg'
        )

        self.assertEqual(response.status_code, 200)
        compress.assert_called_once_with(
            'https://example.com/image.jpg', 40, 640, 45, 'webp'
        )
        self.assertEqual(response.content_type, 'image/webp')
        self.assertIn('private', response.headers['Cache-Control'])
        self.assertIn('max-age=86400', response.headers['Cache-Control'])


if __name__ == '__main__':
    unittest.main()
