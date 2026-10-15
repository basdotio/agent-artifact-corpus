import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from media_host import upload

class HostingTests(unittest.TestCase):
 def test_tmpfiles_uses_actual_download_link(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'input.mp4';path.write_bytes(b'video')
   posted=Mock();posted.json.return_value={'data':{'url':'https://tmpfiles.org/123/input.mp4'}}
   page=Mock();page.text='<a href="https://tmpfiles.org/dl/123/extra-token/input.mp4">Download</a>'
   media=Mock();media.headers={'Content-Type':'video/mp4'};media.iter_content.return_value=iter([b'\x00\x00\x00 ftypisom'])
   context=Mock();context.__enter__=Mock(return_value=media);context.__exit__=Mock(return_value=False)
   with patch('media_host.setting',return_value='tmpfiles'),patch('media_host.requests.post',return_value=posted),patch('media_host.requests.get',side_effect=[page,context]) as get:
    url=upload(path)
    self.assertEqual(url,'https://tmpfiles.org/dl/123/extra-token/input.mp4')
    self.assertEqual(get.call_args.args[0],url)

class FallbackTests(unittest.TestCase):
 def test_primary_failure_uses_configured_fallback(self):
  def settings(k,d=''):return {'MEDIA_HOST':'tmpfiles','MEDIA_HOST_FALLBACKS':'catbox'}.get(k,d)
  with patch('media_host.setting',side_effect=settings),patch('media_host.time.sleep'),patch('media_host._upload_once',side_effect=[ValueError('bad'),ValueError('bad'),'https://files.catbox.moe/test.mp4']) as send:
   self.assertEqual(upload('test.mp4'),'https://files.catbox.moe/test.mp4')
   self.assertEqual([c.args[1] for c in send.call_args_list],['tmpfiles','tmpfiles','catbox'])
 def test_disabled_fallback_does_not_switch(self):
  def settings(k,d=''):return {'MEDIA_HOST':'tmpfiles','MEDIA_HOST_FALLBACKS':''}.get(k,d)
  with patch('media_host.setting',side_effect=settings),patch('media_host.time.sleep'),patch('media_host._upload_once',side_effect=ValueError('bad')) as send:
   with self.assertRaises(RuntimeError):upload('test.mp4')
   self.assertEqual(send.call_count,2)
 def test_success_never_calls_fallback(self):
  with patch('media_host.setting',side_effect=lambda k,d='':d),patch('media_host._upload_once',return_value='https://tmpfiles.org/dl/test.mp4') as send:
   upload('test.mp4');self.assertEqual(send.call_count,1)
