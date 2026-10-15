"""Local UI/API regressions using ASGI; no provider calls or reference media."""
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image
import app
from fixture_helpers import prepared_fixture
import mask_review


class LocalUiTests(unittest.TestCase):
    def test_ui_health_and_original_icons_are_served(self):
        with TestClient(app.app,base_url='http://127.0.0.1') as client:
            self.assertEqual(client.get('/health').json()['service'], 'Genjutsu Skill')
            page = client.get('/')
            self.assertEqual(page.status_code, 200)
            self.assertIn('Genjutsu Skill', page.text)
            self.assertNotIn('Join the waitlist', page.text)
            for name in ('video.webp', 'language.webp', 'seedance-2-5.webp'):
                asset = client.get('/static/companions/' + name)
                self.assertEqual(asset.status_code, 200)
                with Image.open(io.BytesIO(asset.content)) as image:
                    self.assertEqual(image.size, (256, 256))

    def test_invalid_reference_never_reaches_submission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ident = 'a' * 32
            folder = root / ident
            folder.mkdir()
            prepared_fixture(folder)
            mask_review.review(folder, True, 'Mock test fixture', mask_review.fingerprint(folder))
            with patch.object(app, 'RUNS', root), patch('seedance_bridge.submit') as submit:
                with TestClient(app.app,base_url='http://127.0.0.1') as client:
                    response = client.post('/jobs/' + ident + '/seedance', data={'prompt': 'Replace one subject'},
                                           files={'sirio': ('bad.png', b'invalid image', 'image/png')})
                self.assertEqual(response.status_code, 400)
                submit.assert_not_called()

    def test_manual_import_preserves_existing_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ident = 'b' * 32
            folder = root / ident
            folder.mkdir()
            (folder / 'upload.mp4').write_bytes(b'original')
            (folder / 'final-preview.mp4').write_bytes(b'accepted output')
            with patch.object(app, 'RUNS', root), TestClient(app.app,base_url='http://127.0.0.1') as client:
                response = client.post('/jobs/' + ident + '/finish', files={'video': ('result.mp4', b'new', 'video/mp4')})
            self.assertEqual(response.status_code, 409)
            self.assertEqual((folder / 'final-preview.mp4').read_bytes(), b'accepted output')

    def test_cross_origin_post_cannot_start_paid_preparation(self):
        with patch.object(app,'run') as prepare,TestClient(app.app,base_url='http://127.0.0.1') as client:
            response=client.post('/jobs',headers={'Origin':'https://untrusted.example'},files={'video':('clip.mp4',b'untrusted','video/mp4')})
            self.assertEqual(response.status_code,403)
            prepare.assert_not_called()

    def test_unexpected_host_is_rejected(self):
        with TestClient(app.app,base_url='http://127.0.0.1') as client:
            self.assertEqual(client.get('/health',headers={'Host':'untrusted.example'}).status_code,400)

    def test_cross_site_fetch_metadata_is_rejected_even_without_origin(self):
        with patch.object(app,'run') as prepare,TestClient(app.app,base_url='http://127.0.0.1') as client:
            response=client.post('/jobs',headers={'Sec-Fetch-Site':'cross-site'})
            self.assertEqual(response.status_code,403)
            prepare.assert_not_called()


if __name__ == '__main__':
    unittest.main()
