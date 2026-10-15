"""Synthetic media and mocked provider receipts: no network or paid calls."""
from fractions import Fraction
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'assets' / 'workflow'))
import av
import numpy as np
from PIL import Image
import preflight
import pipeline
import audio_workflow
import raw_masks
from job_state import durable_submit, atomic_json


def video(path, seconds=.5, audio=True, silence=False, incompatible=False):
    codec = 'libvpx' if incompatible else 'libx264'
    with av.open(str(path), 'w') as out:
        stream = out.add_stream(codec, rate=24)
        stream.width = stream.height = 16
        stream.pix_fmt = 'yuv420p'
        if audio:
            sound = out.add_stream('pcm_s16le' if incompatible else 'aac', rate=44100)
            sound.layout = 'stereo'
        for index in range(round(seconds * 24)):
            frame = av.VideoFrame.from_ndarray(np.full((16, 16, 3), index % 255, dtype=np.uint8), format='rgb24')
            frame.pts = index
            frame.time_base = Fraction(1, 24)
            for packet in stream.encode(frame):
                out.mux(packet)
        for packet in stream.encode():
            out.mux(packet)
        if audio:
            count = round(seconds * 44100)
            signal = np.zeros(count, np.float32) if silence else np.sin(np.arange(count) * .0627).astype(np.float32) * .2
            values = np.stack([signal, signal])
            for index in range(0, count, 1024):
                frame = av.AudioFrame.from_ndarray(np.ascontiguousarray(values[:, index:index+1024]), format='fltp', layout='stereo')
                frame.sample_rate = 44100
                frame.pts = index
                for packet in sound.encode(frame):
                    out.mux(packet)
            for packet in sound.encode():
                out.mux(packet)
    return path


class Response:
    def __init__(self, data=None, content=b''):
        self.data = data
        self.content = content
    def json(self):
        return self.data
    def raise_for_status(self):
        return None


class PreparationGuards(unittest.TestCase):
    def setUp(self):
        self.scratch = ROOT.parent / '.genjutsu-test-temporary'
        self.scratch.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=self.scratch)
        self.folder = Path(self.temporary.name)
        self.source = video(self.folder / 'source.mp4')
        self.env = patch.dict(os.environ, {'REPLICATE_API_TOKEN': 'offline-test-placeholder'})
        self.env.start()
    def tearDown(self):
        self.env.stop()
        assert self.folder.resolve().is_relative_to(self.scratch.resolve())
        self.temporary.cleanup()

    def test_valid_source_has_decoded_audio_and_actual_mux_report(self):
        report = preflight.inspect_source(self.source)
        self.assertEqual(report['frames'], 12)
        self.assertGreater(report['audio_samples'], 0)
        self.assertTrue(report['original_mp4_packet_copy'])
        json.dumps(report, allow_nan=False)

    def test_no_audio_and_silent_audio_reject_before_provider(self):
        for source in (video(self.folder/'no-audio.mp4', audio=False), video(self.folder/'silent.mp4', silence=True)):
            with patch('requests.post', side_effect=AssertionError('Network called')), patch('requests.get', side_effect=AssertionError('Network called')):
                with self.assertRaisesRegex(ValueError, 'audio'):
                    pipeline.run(source, self.folder/'bad-job')

    def test_long_source_rejects_before_provider_in_all_modes(self):
        source = video(self.folder/'long.mp4', seconds=31)
        import face_mesh
        for prepare in (pipeline.run, face_mesh.run, face_mesh.run_depth):
            with patch('requests.post', side_effect=AssertionError('Network called')), patch('requests.get', side_effect=AssertionError('Network called')):
                with self.assertRaisesRegex(ValueError, '30 seconds'):
                    prepare(source, self.folder/'bad-job')

    def test_packet_copy_incompatible_original_is_rejected(self):
        source = video(self.folder/'unsupported.mkv', incompatible=True)
        with self.assertRaisesRegex(ValueError, 'cannot be copied into MP4'):
            preflight.inspect_source(source)

    def test_rubberband_missing_blocks_prepare_but_not_media_inspection(self):
        with patch('preflight.shutil.which', return_value=None):
            self.assertTrue(preflight.inspect_source(self.source)['frames'])
            with self.assertRaisesRegex(ValueError, 'Rubber Band'):
                pipeline.run(self.source, self.folder/'blocked')

    def test_mesh_dependency_failure_precedes_hosted_work(self):
        import face_mesh
        with patch('preflight._mesh_ready', side_effect=ValueError('mesh model missing')), patch('requests.post', side_effect=AssertionError('Network called')):
            with self.assertRaisesRegex(ValueError, 'mesh model missing'):
                face_mesh.run_depth(self.source, self.folder/'blocked')

    def test_references_decode_and_reject_unsupported_secondary_video(self):
        picture = self.folder/'ref.png'
        Image.new('RGB', (8, 8), 'red').save(picture)
        self.assertEqual(preflight.inspect_reference(picture)['type'], 'image')
        self.assertEqual(preflight.inspect_reference(video(self.folder/'ref.mp4', audio=False))['type'], 'video')
        with self.assertRaisesRegex(ValueError, 'Secondary'):
            preflight.inspect_reference(self.source, secondary=True)
        picture.write_bytes(b'broken image')
        with self.assertRaisesRegex(ValueError, 'cannot be decoded'):
            preflight.inspect_reference(picture)
        disguised = self.folder/'disguised.png'
        Image.new('RGB', (8, 8)).save(disguised, format='GIF')
        with self.assertRaisesRegex(ValueError, 'JPEG, PNG, or WebP'):
            preflight.inspect_reference(disguised)

    def test_omni_duration_rejects_incompatible_rounding_and_short_sources(self):
        for seconds in (4.6, 3.0, 3.5, 5.6):
            with self.subTest(seconds=seconds), self.assertRaisesRegex(ValueError, 'timing is incompatible'):
                preflight.omni_duration(seconds)
        for seconds in (float('nan'), float('inf'), 0, -1, 31):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                preflight.omni_duration(seconds)

    def test_omni_duration_accepts_exact_and_existing_small_hold_policy(self):
        self.assertEqual(preflight.omni_duration(5), 5)
        self.assertEqual(preflight.omni_duration(4.4), 4)
        self.assertEqual(preflight.omni_duration(4.5), 4)
        self.assertEqual(preflight.omni_duration(4.75), 5)
        self.assertEqual(preflight.omni_duration(5.0, 5.4), 5)
        with self.assertRaisesRegex(ValueError, 'timing is incompatible'):
            preflight.omni_duration(5.0, 4.6)

    def test_video_reference_preflight_checks_projected_and_original_timing(self):
        reference = video(self.folder/'identity.mp4', audio=False)
        for seconds in (4.6, 3.0):
            source = video(self.folder/f'source-{seconds}.mp4', seconds=seconds)
            with patch('requests.post', side_effect=AssertionError('Network called')), patch('requests.get', side_effect=AssertionError('Network called')):
                with self.assertRaisesRegex(ValueError, 'timing is incompatible'):
                    preflight.preflight_job(source, reference=reference, require_dependencies=False, require_rubberband=False)
        source = video(self.folder/'exact-five.mp4', seconds=5)
        report = preflight.preflight_job(source, reference=reference, require_dependencies=False, require_rubberband=False)
        self.assertEqual(report['omni_duration_seconds'], 5)
        self.assertEqual(report['source']['container_duration'], 5)
        picture = self.folder/'identity.png'
        Image.new('RGB', (8,8), 'red').save(picture)
        image_report = preflight.preflight_job(self.source, reference=picture, require_dependencies=False, require_rubberband=False)
        self.assertNotIn('omni_duration_seconds', image_report)

    def test_partial_preparation_source_and_settings_changes_reject(self):
        job = self.folder/'job'
        job.mkdir()
        report = {'source': preflight.inspect_source(self.source), 'mode': 'depth', 'provider': 'replicate'}
        preflight.bind_preparation(job, report)
        context = json.loads((job/'workflow-mode.json').read_text())
        self.assertEqual(context, {'mode':'depth','provider':'replicate','subject':'person'})
        with self.assertRaisesRegex(ValueError, 'changed'):
            preflight.bind_preparation(job, report, 'dog')
        video(self.source, seconds=.75)
        report['source'] = preflight.inspect_source(self.source)
        with self.assertRaisesRegex(ValueError, 'changed'):
            preflight.bind_preparation(job, report)

    def test_submitted_generation_blocks_preparation_under_runner_lock(self):
        job = self.folder/'submitted'
        job.mkdir()
        atomic_json(job/'.submission-seedance-draft.json', {'state':'ambiguous'})
        report = {'source':preflight.inspect_source(self.source),'mode':'depth','provider':'replicate'}
        with self.assertRaisesRegex(ValueError, 'already submitted or attempted'):
            preflight.bind_preparation(job, report)

    def test_encoding_dependency_failure_precedes_any_hosted_work(self):
        with patch('preflight._encoding_ready', side_effect=ValueError('encoder unavailable')), patch('requests.post', side_effect=AssertionError('Network called')):
            with self.assertRaisesRegex(ValueError, 'encoder unavailable'):
                pipeline.run(self.source, self.folder/'blocked')

    def test_final_original_audio_compressed_packets_are_preserved(self):
        job = self.folder/'export'
        job.mkdir()
        __import__('shutil').copy2(self.source, job/'upload.mp4')
        generated = video(job/'generated.mp4', audio=False)
        result = audio_workflow.finish_preview(generated, job)
        def audio_packets(path):
            with av.open(str(path)) as container:
                return [bytes(packet) for packet in container.demux(audio=0) if packet.dts is not None]
        self.assertEqual(audio_packets(self.source), audio_packets(result))

    def test_depth_accepted_receipt_resume_never_posts_or_uploads(self):
        output = self.folder/'depth-raw.mp4'
        identity = {'source':preflight.file_identity(self.source),'model':'lucataco/depth-anything-video','stage':'depth-v1'}
        prediction = {'id':'depth-paid-id','status':'succeeded','output':'https://offline/depth.mp4'}
        durable_submit(self.folder, 'depth', {}, lambda: prediction, identity)
        with patch('requests.post', side_effect=AssertionError('Repeated POST')), patch('requests.get', return_value=Response(content=self.source.read_bytes())):
            pipeline.depth_replicate(self.source, output)
            pipeline.depth_replicate(self.source, output)
        self.assertEqual(json.loads((self.folder/'depth-prediction.json').read_text())['id'], 'depth-paid-id')

    def test_sam_accepted_receipt_resume_and_stale_frames_removed(self):
        version = '408f82fc20c300aac5d61d2e34ddb34cd0181e810e9f609d250aed14d5f81269'
        identity = {'video':preflight.file_identity(self.source),'version':version,'prompt':'person','mask_only':True,'return_zip':True}
        prediction = {'id':'sam-paid-id','status':'succeeded','output':'https://offline/masks.zip'}
        durable_submit(self.folder, 'sam', {}, lambda: prediction, identity)
        archive = io.BytesIO()
        image = io.BytesIO()
        Image.new('L', (8,8), 255).save(image, format='PNG')
        with zipfile.ZipFile(archive, 'w') as zipped:
            zipped.writestr('nested/mask_000000.png', image.getvalue())
        stale = self.folder/'raw-masks'
        stale.mkdir()
        (stale/'mask_999999.png').write_bytes(image.getvalue())
        with patch('requests.post', side_effect=AssertionError('Repeated POST')), patch('requests.get', return_value=Response(content=archive.getvalue())):
            result = raw_masks.segment_raw(self.source, self.folder)
            raw_masks.segment_raw(self.source, self.folder)
        self.assertEqual([p.name for p in result.glob('mask_*.png')], ['mask_000000.png'])

    def test_demucs_resume_and_tampered_audio_cache_blocks_reuse(self):
        report = preflight.inspect_source(self.source)
        identity = {'source':{k:report[k] for k in ('sha256','bytes')},'model':'htdemucs','version':'25a173108cff36ef9f80f854c162d01df9e6528be175794b81158fa03836d953','stage':'audio-v1'}
        prediction = {'id':'demucs-paid-id','status':'succeeded','output':{'vocals':'https://offline/vocals','other':'https://offline/other'}}
        durable_submit(self.folder, 'demucs', {}, lambda: prediction, identity)
        sound = self.folder/'stem.wav'
        audio_workflow.write_audio(sound, audio_workflow.read_audio(self.source))
        with patch('requests.post', side_effect=AssertionError('Repeated POST')), patch('requests.get', return_value=Response(content=sound.read_bytes())):
            audio_workflow.separate(self.source, self.folder, lambda _: None)
            audio_workflow.separate(self.source, self.folder, lambda _: None)
        (self.folder/'vocals.wav').write_bytes(b'tampered')
        with patch('requests.post', side_effect=AssertionError('Repeated POST')):
            with self.assertRaisesRegex(ValueError, 'artifact changed'):
                audio_workflow.separate(self.source, self.folder, lambda _: None)

    def test_ambiguous_depth_submission_stops_before_any_remote_call(self):
        identity = {'source':preflight.file_identity(self.source),'model':'lucataco/depth-anything-video','stage':'depth-v1'}
        with self.assertRaisesRegex(ValueError, 'uncertain'):
            durable_submit(self.folder, 'depth', {}, lambda: (_ for _ in ()).throw(TimeoutError()), identity)
        with patch('requests.post', side_effect=AssertionError('Repeated POST')), patch('requests.get', side_effect=AssertionError('Remote called')):
            with self.assertRaisesRegex(ValueError, 'unresolved'):
                pipeline.depth_replicate(self.source, self.folder/'depth-raw.mp4')


if __name__ == '__main__':
    unittest.main()
