import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch,Mock
import mask_review,seedance_bridge
from fixture_helpers import prepared_fixture

class WorkflowTests(unittest.TestCase):
 def test_mask_changed_invalidates_approval(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   prepared_fixture(p)
   fingerprint=mask_review.fingerprint(p)
   mask_review.review(p,True,'Entire clip reviewed',fingerprint)
   mask_review.require_approved(p)
   (p/'mask.mp4').write_bytes(b'changed')
   with self.assertRaises(ValueError):mask_review.require_approved(p)
   with self.assertRaises(ValueError):mask_review.review(p,True,'stale',fingerprint)
 def test_existing_submission_not_requeued(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);reference=prepared_fixture(p);(p/'seedance-response.json').write_text('{}')
   with patch('mask_review.require_approved'),patch('seedance_bridge.requests.post') as post:
    with self.assertRaises(ValueError):seedance_bridge.submit(p,'prompt',reference)
    post.assert_not_called()
 def test_edit_draft_self_contained(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);reference=prepared_fixture(p)
   response=Mock();response.json.return_value={'requestId':'fake-id'}
   with patch('mask_review.require_approved'),patch('seedance_bridge.credential',return_value='test'),patch('seedance_bridge.setting',return_value='https://example.org/callback'),patch('seedance_bridge.upload',return_value='https://example.org/media'),patch('audio_workflow.prepare_seedance_video',return_value=p/'seedance-input.mp4'),patch('seedance_bridge.requests.post',return_value=response) as post:
    seedance_bridge.submit(p,'Replace one subject',reference)
    payload=post.call_args.kwargs['json']
    self.assertTrue(payload['is_draft']);self.assertEqual(payload['mode'],'edit');self.assertEqual(payload['audios'],[]);self.assertEqual(len(payload['videos']),1)
    self.assertTrue((p/'generation.json').exists())
 def test_collection_downloads_and_restores(self):
  with tempfile.TemporaryDirectory() as d:
   (Path(d)/'upload.mp4').write_bytes(b'original')
   response=Mock();response.json.return_value={'status':'COMPLETED','result':'https://example.org/result.mp4'}
   media=Mock();media.content=b'video'
   def create_preview(generated,folder):(Path(folder)/'final-preview.mp4').write_bytes(b'exported')
   with patch('seedance_bridge.credential',return_value='test'),patch('seedance_bridge.requests.post',return_value=response),patch('seedance_bridge.requests.get',return_value=media),patch('seedance_bridge.finish_preview',side_effect=create_preview) as restore:
    seedance_bridge.wait_and_finish(d,'fake-id')
    self.assertEqual((Path(d)/'seedance-result.mp4').read_bytes(),b'video');restore.assert_called_once()
 def test_hd_only_reuses_draft(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   for name in ['upload.mp4','final-preview.mp4']:(p/name).write_bytes(b'test')
   (p/'generation.json').write_text(json.dumps({'request_id':'draft'}))
   (p/'seedance-request.json').write_text(json.dumps({'is_draft':True,'webhook_url':''}))
   response=Mock();response.json.return_value={'requestId':'hd-id'}
   with patch('seedance_bridge.credential',return_value='test'),patch('seedance_bridge.setting',return_value='https://current.example.org/callback'),patch('seedance_bridge.requests.post',return_value=response) as post:
    self.assertEqual(seedance_bridge.submit_hd(p),'hd-id')
    self.assertEqual(post.call_args.kwargs['json'],{'draft_id':'draft','webhook_url':'https://current.example.org/callback'})
    self.assertEqual(seedance_bridge.submit_hd(p),'hd-id')
    post.assert_called_once()

if __name__=='__main__':unittest.main()
