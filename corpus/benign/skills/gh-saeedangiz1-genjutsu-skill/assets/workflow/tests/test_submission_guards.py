"""No-network checks for review identity, billed POST durability and collection."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

import requests
from PIL import Image
import av
import numpy as np
from fractions import Fraction

from job_state import atomic_json, durable_submit, job_lock, load_submission
import mask_review
import seedance_bridge


def prepared(folder, mode="depth"):
    folder = Path(folder)
    for name in mask_review.COMMON_FILES:
        (folder / name).write_bytes((name + "-original").encode())
    atomic_json(folder / "audio-manifest.json", {"embedded_vocals": "vocals-plus3.wav", "pitch_semitones": 3})
    (folder / "vocals-plus3.wav").write_bytes(b"pitched vocals")
    atomic_json(folder / "workflow-mode.json", {"mode": mode})
    if mode in ("depth", "depth_mesh"):
        (folder / "depth.mp4").write_bytes(b"depth")
        (folder / "mask.mp4").write_bytes(b"mask")
    if mode in ("face_mesh", "depth_mesh"):
        atomic_json(folder / "face-landmarks.json", {"frames": []})
    if mode == "depth_mesh":
        (folder / "depth-composite-silent.mp4").write_bytes(b"depth composite")
    reference = folder / "reference.png"
    Image.new('RGB', (4, 4), (30, 60, 90)).save(reference)
    mask_review.review(folder, True, "Entire input and dialogue reviewed", mask_review.fingerprint(folder))
    return reference


def settings(name, default=""):
    return {"ENHANCOR_BASE_URL": "https://provider.example/api", "ENHANCOR_WEBHOOK_URL": "https://current.example/callback"}.get(name, default)


def queued(ident="draft-id"):
    response = Mock()
    response.json.return_value = {"requestId": ident}
    return response


def restored(generated, folder):
    (Path(folder) / "final-preview.mp4").write_bytes(b"video with restored original audio")


def synthetic_video(path, seconds, audio=True):
    """Small real MP4 for duration/routing checks, without external media."""
    with av.open(str(path), 'w') as output:
        video = output.add_stream('libx264', rate=24)
        video.width = video.height = 32
        video.pix_fmt = 'yuv420p'
        sound = output.add_stream('aac', rate=44100) if audio else None
        if sound is not None:
            sound.layout = 'stereo'
        for index in range(round(seconds * 24)):
            frame = av.VideoFrame.from_ndarray(np.full((32, 32, 3), 60, dtype=np.uint8), format='rgb24')
            frame.pts = index
            frame.time_base = Fraction(1, 24)
            for packet in video.encode(frame):
                output.mux(packet)
        for packet in video.encode():
            output.mux(packet)
        if sound is not None:
            count = round(seconds * 44100)
            wave = (np.sin(np.arange(count) * 2 * np.pi * 440 / 44100) * .1).astype(np.float32)
            samples = np.tile(wave, (2, 1))
            for index in range(0, count, 4096):
                frame = av.AudioFrame.from_ndarray(np.ascontiguousarray(samples[:, index:index + 4096]), format='fltp', layout='stereo')
                frame.sample_rate = 44100
                frame.pts = index
                for packet in sound.encode(frame):
                    output.mux(packet)
            for packet in sound.encode():
                output.mux(packet)


class DurableStateTests(unittest.TestCase):
    def test_atomic_json_replaces_valid_state_without_temporary_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            atomic_json(path, {"version": 1})
            atomic_json(path, {"version": 2, "text": "日本語"})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["version"], 2)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_accepted_response_resumes_without_sending_again(self):
        with tempfile.TemporaryDirectory() as directory:
            send = Mock(return_value={"id": "accepted"})
            first = durable_submit(directory, "depth", {"input": "url"}, send, {"source": "hash"})
            resumed = durable_submit(directory, "depth", {"input": "refreshed-upload-url"}, send, {"source": "hash"})
            self.assertEqual(first, resumed)
            self.assertEqual(load_submission(directory, "depth", {"source": "hash"}), first)
            send.assert_called_once()
            with self.assertRaisesRegex(ValueError, "changed"):
                durable_submit(directory, "depth", {}, send, {"source": "different"})

    def test_pending_intent_exists_before_send_and_ambiguous_timeout_is_not_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            def send():
                with self.assertRaisesRegex(ValueError, "unresolved"):
                    load_submission(directory, "demucs")
                raise requests.Timeout("The provider may have accepted the request")
            with self.assertRaisesRegex(ValueError, "uncertain"):
                durable_submit(directory, "demucs", {"audio": "url"}, send)
            retry = Mock(return_value={"id": "duplicate"})
            with self.assertRaisesRegex(ValueError, "unresolved"):
                durable_submit(directory, "demucs", {"audio": "url"}, retry)
            retry.assert_not_called()
            record = json.loads((Path(directory) / ".submission-demucs.json").read_text())
            self.assertEqual(record["state"], "ambiguous")
            self.assertEqual(record["error_type"], "Timeout")

    def test_saved_pending_after_crash_blocks_send(self):
        with tempfile.TemporaryDirectory() as directory:
            atomic_json(Path(directory) / ".submission-sam.json", {"version": 1, "stage": "sam", "state": "pending"})
            send = Mock()
            with self.assertRaises(ValueError):
                durable_submit(directory, "sam", {}, send)
            send.assert_not_called()

    def test_unsafe_stage_names_and_corrupt_records_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            for stage in ("../escape", "bad/name", "", "with space"):
                with self.subTest(stage=stage), self.assertRaises(ValueError):
                    load_submission(directory, stage)
            (Path(directory) / ".submission-depth.json").write_text("{")
            with self.assertRaisesRegex(ValueError, "unreadable"):
                load_submission(directory, "depth")

    def test_simultaneous_submitters_send_only_once(self):
        with tempfile.TemporaryDirectory() as directory:
            entered, release = threading.Event(), threading.Event()
            result = []
            def send():
                entered.set()
                if not release.wait(5):
                    raise RuntimeError("test synchronization failed")
                return {"id": "single"}
            def first():
                try:
                    result.append(durable_submit(directory, "sam", {}, send))
                except BaseException as exc:
                    result.append(exc)
            worker = threading.Thread(target=first)
            worker.start()
            try:
                self.assertTrue(entered.wait(5))
                duplicate = Mock()
                with self.assertRaisesRegex(ValueError, "busy"):
                    durable_submit(directory, "sam", {}, duplicate)
                duplicate.assert_not_called()
            finally:
                release.set()
                worker.join(5)
            self.assertEqual(result, [{"id": "single"}])

    def test_cross_process_lock_is_released_after_process_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            script = (
                "import sys;sys.path.insert(0,sys.argv[2]);from job_state import job_lock;"
                "lock=job_lock(sys.argv[1]);lock.__enter__();print('held',flush=True);sys.stdin.readline()"
            )
            worker = subprocess.Popen(
                [sys.executable, "-S", "-c", script, directory, str(Path(seedance_bridge.__file__).parent)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            try:
                self.assertEqual(worker.stdout.readline().strip(), "held")
                with self.assertRaisesRegex(ValueError, "busy"):
                    with job_lock(directory):
                        self.fail("cross-process lock unexpectedly acquired")
                worker.terminate()
                worker.communicate(timeout=5)
                with job_lock(directory):
                    self.assertTrue((Path(directory) / ".lock-job").exists())
            finally:
                if worker.poll() is None:
                    worker.kill()
                    worker.communicate(timeout=5)


class InputBindingTests(unittest.TestCase):
    def test_all_modes_bind_approval_to_prepared_source_and_audio(self):
        for mode in ("depth", "face_mesh", "depth_mesh"):
            for name in ("seedance-input.mp4", "upload.mp4", "original-audio.wav", "vocals.wav", "vocals-plus3.wav", "audio-manifest.json"):
                with self.subTest(mode=mode, file=name), tempfile.TemporaryDirectory() as directory:
                    prepared(directory, mode)
                    path = Path(directory) / name
                    if name.endswith(".json"):
                        atomic_json(path, {"embedded_vocals": "vocals-plus3.wav", "pitch_semitones": 4})
                    else:
                        path.write_bytes(b"changed after approval")
                    self.assertFalse(mask_review.state(directory)["approved"])
                    with self.assertRaisesRegex(ValueError, "review required"):
                        mask_review.require_approved(directory)

    def test_review_cannot_be_recorded_while_preparation_or_submission_is_active(self):
        with tempfile.TemporaryDirectory() as directory:
            prepared(directory)
            with job_lock(directory):
                with self.assertRaisesRegex(ValueError, "busy"):
                    mask_review.review(directory, True, "raced", mask_review.fingerprint(directory))

    def test_corrupt_review_can_be_reapproved_but_is_never_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            prepared(directory)
            (Path(directory) / 'mask-review.json').write_text('{broken')
            state = mask_review.state(directory)
            self.assertFalse(state['approved'])
            self.assertEqual(state['status'], 'pending')
            with self.assertRaises(ValueError):
                mask_review.require_approved(directory)
            mask_review.review(directory, True, 'Rechecked intact assets', state['fingerprint'])
            mask_review.require_approved(directory)

    def test_submission_uploads_exact_reviewed_input_without_rebuilding_all_modes(self):
        for mode in ("depth", "face_mesh", "depth_mesh"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                reference = prepared(directory, mode)
                with patch("seedance_bridge.setting", side_effect=settings), patch("seedance_bridge.credential", return_value="test"), patch("seedance_bridge.upload", return_value="https://media.example/file") as upload, patch("seedance_bridge.requests.post", return_value=queued()) as post, patch("audio_workflow.prepare_seedance_video") as rebuild:
                    self.assertEqual(seedance_bridge.submit(directory, "Replace character", reference, status=lambda _: None), "draft-id")
                    rebuild.assert_not_called()
                    self.assertIn(Path(directory) / "seedance-input.mp4", [item.args[0] for item in upload.call_args_list])
                    payload = post.call_args.kwargs["json"]
                    self.assertTrue(payload["is_draft"])
                    self.assertEqual(payload["audios"], [])
                    if mode != "depth":
                        self.assertIn("Remove all face mesh lines", payload["prompt"])

    def test_resume_binds_prompt_and_reference_content_but_not_its_filepath(self):
        with tempfile.TemporaryDirectory() as directory:
            reference = prepared(directory)
            with patch("seedance_bridge.setting", side_effect=settings), patch("seedance_bridge.credential", return_value="test"), patch("seedance_bridge.upload", return_value="https://media.example/file") as upload, patch("seedance_bridge.requests.post", return_value=queued()) as post:
                seedance_bridge.submit(directory, "Exact prompt", reference, status=lambda _: None)
                relocated = Path(directory) / "relocated.png"
                relocated.write_bytes(reference.read_bytes())
                self.assertEqual(seedance_bridge.submit(directory, "Exact prompt", relocated, status=lambda _: None), "draft-id")
                self.assertEqual(post.call_count, 1)
                self.assertEqual(upload.call_count, 2)
                with self.assertRaisesRegex(ValueError, "changed"):
                    seedance_bridge.submit(directory, "Different prompt", reference)
                Image.new('RGB', (4, 4), (90, 60, 30)).save(reference)
                with self.assertRaisesRegex(ValueError, "changed"):
                    seedance_bridge.submit(directory, "Exact prompt", reference)
                self.assertEqual(post.call_count, 1)

    def test_changed_input_after_review_cannot_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            reference = prepared(directory)
            (Path(directory) / "seedance-input.mp4").write_bytes(b"different video")
            with patch("seedance_bridge.requests.post") as post:
                with self.assertRaisesRegex(ValueError, "review required"):
                    seedance_bridge.submit(directory, "Prompt", reference)
                post.assert_not_called()

    def test_invalid_reference_fails_before_hosting_or_queueing(self):
        with tempfile.TemporaryDirectory() as directory:
            reference = prepared(directory)
            reference.write_bytes(b"not an image")
            with patch("seedance_bridge.upload") as hosting, patch("seedance_bridge.requests.post") as post:
                with self.assertRaisesRegex(ValueError, "cannot be decoded"):
                    seedance_bridge.submit(directory, "Prompt", reference)
                hosting.assert_not_called()
                post.assert_not_called()

    def test_accepted_draft_repairs_auxiliary_state_after_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            reference = prepared(directory)
            with patch("seedance_bridge.setting", side_effect=settings), patch("seedance_bridge.credential", return_value="test"), patch("seedance_bridge.upload", return_value="https://media.example/file"), patch("seedance_bridge.requests.post", return_value=queued()) as post:
                seedance_bridge.submit(folder, "Prompt", reference, status=lambda _: None)
                (folder / "seedance-response.json").unlink()
                (folder / "generation.json").unlink()
                self.assertEqual(seedance_bridge.submit(folder, "Prompt", reference, status=lambda _: None), "draft-id")
                self.assertTrue((folder / "seedance-response.json").exists())
                self.assertTrue((folder / "generation.json").exists())
                post.assert_called_once()

    def test_reference_edit_during_upload_cannot_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            reference = prepared(directory)
            def mutate(path):
                if Path(path) == reference:
                    Image.new('RGB', (4, 4), (90, 60, 30)).save(reference)
                return "https://media.example/file"
            with patch("seedance_bridge.setting", side_effect=settings), patch("seedance_bridge.credential", return_value="test"), patch("seedance_bridge.upload", side_effect=mutate), patch("seedance_bridge.requests.post") as post:
                with self.assertRaisesRegex(ValueError, "changed during upload"):
                    seedance_bridge.submit(directory, "Prompt", reference)
                post.assert_not_called()

    def test_real_video_reference_rejects_incompatible_duration_before_hosting(self):
        for source_seconds, prepared_seconds in ((1.0, 1.0), (4.6, 4.6), (4.6, 4.2)):
            with self.subTest(source=source_seconds, prepared=prepared_seconds), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                prepared(folder)
                synthetic_video(folder / 'upload.mp4', source_seconds)
                synthetic_video(folder / 'seedance-input.mp4', prepared_seconds)
                reference = folder / 'identity-reference.mp4'
                synthetic_video(reference, 1.0, audio=False)
                mask_review.review(folder, True, 'Rechecked real input and duration', mask_review.fingerprint(folder))
                with patch('seedance_bridge.setting', side_effect=settings), patch('seedance_bridge.credential', return_value='test'), patch('seedance_bridge.upload') as hosting, patch('seedance_bridge.requests.post') as post:
                    with self.assertRaises(ValueError):
                        seedance_bridge.submit(folder, 'Replace using reference video', reference, status=lambda _: None)
                    hosting.assert_not_called()
                    post.assert_not_called()
                    self.assertFalse((folder / '.submission-seedance-draft.json').exists())

    def test_real_compatible_video_reference_routes_exact_input_and_optional_secondary(self):
        for secondary in (False, True):
            with self.subTest(secondary=secondary), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                image = prepared(folder)
                synthetic_video(folder / 'upload.mp4', 4.2)
                synthetic_video(folder / 'seedance-input.mp4', 4.2)
                reference = folder / 'identity-reference.mp4'
                synthetic_video(reference, 1.0, audio=False)
                mask_review.review(folder, True, 'Real compatible prepared input reviewed', mask_review.fingerprint(folder))
                def hosting(path):
                    return 'https://media.example/' + Path(path).name
                with patch('seedance_bridge.setting', side_effect=settings), patch('seedance_bridge.credential', return_value='test'), patch('seedance_bridge.upload', side_effect=hosting) as upload, patch('seedance_bridge.requests.post', return_value=queued()) as post, patch('audio_workflow.prepare_seedance_video') as rebuild:
                    seedance_bridge.submit(folder, 'Use @Video1 timing and @Video2 identity', reference, image if secondary else None, status=lambda _: None)
                    payload = post.call_args.kwargs['json']
                    self.assertEqual(payload['mode'], 'multi_reference')
                    self.assertEqual(payload['duration'], '4')
                    self.assertEqual(payload['aspect_ratio'], '1:1')
                    self.assertEqual(payload['videos'], ['https://media.example/seedance-input.mp4', 'https://media.example/identity-reference.mp4'])
                    self.assertEqual(payload['images'], ['https://media.example/reference.png'] if secondary else [])
                    self.assertIn('@Video1 is the source edit', payload['prompt'])
                    self.assertIn('@Video2 is only the primary character visual identity reference', payload['prompt'])
                    if secondary:
                        self.assertIn('@Image1 is the secondary character visual identity reference', payload['prompt'])
                    self.assertEqual(upload.call_count, 3 if secondary else 2)
                    rebuild.assert_not_called()

    def test_seedance_timeout_and_missing_request_id_never_requeue(self):
        for failure in (requests.Timeout("accepted?"), queued(None)):
            with self.subTest(failure=type(failure).__name__), tempfile.TemporaryDirectory() as directory:
                reference = prepared(directory)
                with patch("seedance_bridge.setting", side_effect=settings), patch("seedance_bridge.credential", return_value="test"), patch("seedance_bridge.upload", return_value="https://media.example/file"), patch("seedance_bridge.requests.post", side_effect=failure if isinstance(failure, Exception) else None, return_value=failure) as post:
                    with self.assertRaisesRegex(ValueError, "uncertain"):
                        seedance_bridge.submit(directory, "Prompt", reference)
                    with self.assertRaisesRegex(ValueError, "unresolved"):
                        seedance_bridge.submit(directory, "Prompt", reference)
                    self.assertEqual(post.call_count, 1)


class HDAndCollectionTests(unittest.TestCase):
    def _draft(self, directory):
        folder = Path(directory)
        (folder / "upload.mp4").write_bytes(b"original source")
        (folder / "final-preview.mp4").write_bytes(b"accepted draft preview")
        atomic_json(folder / "generation.json", {"request_id": "draft-id"})
        atomic_json(folder / "seedance-request.json", {"is_draft": True, "webhook_url": "https://expired.example/callback"})
        return folder

    def test_hd_uses_current_callback_and_resume_keeps_accepted_request(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = self._draft(directory)
            with patch("seedance_bridge.setting", side_effect=settings), patch("seedance_bridge.credential", return_value="test"), patch("seedance_bridge.requests.post", return_value=queued("hd-id")) as post:
                self.assertEqual(seedance_bridge.submit_hd(folder), "hd-id")
                self.assertEqual(post.call_args.kwargs["json"], {"draft_id": "draft-id", "webhook_url": "https://current.example/callback"})
                (folder / "hd" / "response.json").unlink()
                (folder / "hd" / "generation.json").unlink()
                with patch("seedance_bridge.setting", side_effect=lambda name, default="": "https://next.example/callback" if name == "ENHANCOR_WEBHOOK_URL" else settings(name, default)):
                    self.assertEqual(seedance_bridge.submit_hd(folder), "hd-id")
                self.assertTrue((folder / "hd" / "response.json").exists())
                self.assertTrue((folder / "hd" / "generation.json").exists())
                post.assert_called_once()

    def test_hd_timeout_is_not_automatically_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = self._draft(directory)
            with patch("seedance_bridge.setting", side_effect=settings), patch("seedance_bridge.credential", return_value="test"), patch("seedance_bridge.requests.post", side_effect=requests.Timeout()) as post:
                with self.assertRaisesRegex(ValueError, "uncertain"):
                    seedance_bridge.submit_hd(folder)
                with self.assertRaisesRegex(ValueError, "unresolved"):
                    seedance_bridge.submit_hd(folder)
                post.assert_called_once()

    def test_hd_source_change_during_copy_cannot_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = self._draft(directory)
            def changed_copy(source, target):
                Path(source).write_bytes(b'changed original audio')
                Path(target).write_bytes(Path(source).read_bytes())
            with patch('seedance_bridge.setting', side_effect=settings), patch('seedance_bridge.credential', return_value='test'), patch('seedance_bridge._atomic_copy', side_effect=changed_copy), patch('seedance_bridge.requests.post') as post:
                with self.assertRaisesRegex(ValueError, 'changed during HD preparation'):
                    seedance_bridge.submit_hd(folder)
                post.assert_not_called()

    def test_simultaneous_collectors_download_and_restore_only_once(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "upload.mp4").write_bytes(b"original source")
            entered, release = threading.Event(), threading.Event()
            result = []
            response = Mock()
            response.json.return_value = {"status": "COMPLETED", "result": "https://media.example/result.mp4"}
            media = Mock(content=b"provider video")
            def poll(*args, **kwargs):
                entered.set()
                if not release.wait(5):
                    raise RuntimeError("test synchronization failed")
                return response
            def collect():
                try:
                    seedance_bridge.wait_and_finish(folder, "draft-id", status=lambda _: None)
                    result.append("done")
                except BaseException as exc:
                    result.append(exc)
            with patch("seedance_bridge.setting", side_effect=settings), patch("seedance_bridge.credential", return_value="test"), patch("seedance_bridge.requests.post", side_effect=poll) as post, patch("seedance_bridge.requests.get", return_value=media) as download, patch("seedance_bridge.finish_preview", side_effect=restored) as finish:
                worker = threading.Thread(target=collect)
                worker.start()
                try:
                    self.assertTrue(entered.wait(5))
                    with self.assertRaisesRegex(ValueError, "busy"):
                        seedance_bridge.wait_and_finish(folder, "draft-id")
                finally:
                    release.set()
                    worker.join(5)
                self.assertEqual(result, ["done"])
                self.assertEqual((folder / "seedance-result.mp4").read_bytes(), b"provider video")
                self.assertTrue((folder / "final-preview.mp4").is_file())
                seedance_bridge.wait_and_finish(folder, "draft-id", status=lambda _: None)
                post.assert_called_once()
                download.assert_called_once()
                finish.assert_called_once()

    def test_failed_restoration_keeps_download_and_resumes_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "upload.mp4").write_bytes(b"original source")
            response = Mock()
            response.json.return_value = {"status": "COMPLETED", "result": "https://media.example/result.mp4"}
            def failed_restore(generated, target):
                (Path(target) / "final-preview.mp4").write_bytes(b"partial output")
                raise ValueError("duration mismatch")
            with patch("seedance_bridge.setting", side_effect=settings), patch("seedance_bridge.credential", return_value="test"), patch("seedance_bridge.requests.post", return_value=response) as post, patch("seedance_bridge.requests.get", return_value=Mock(content=b"provider video")) as download, patch("seedance_bridge.finish_preview", side_effect=failed_restore):
                with self.assertRaisesRegex(ValueError, "duration mismatch"):
                    seedance_bridge.wait_and_finish(folder, "draft-id", status=lambda _: None)
                self.assertFalse((folder / "final-preview.mp4").exists())
                self.assertEqual((folder / "seedance-result.mp4").read_bytes(), b"provider video")
                with patch("seedance_bridge.finish_preview", side_effect=restored):
                    seedance_bridge.wait_and_finish(folder, "draft-id", status=lambda _: None)
                post.assert_called_once()
                download.assert_called_once()
                self.assertEqual(list(folder.glob(".finish-*")), [])

    def test_existing_output_is_preserved_and_request_identity_is_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = self._draft(directory)
            before = (folder / "final-preview.mp4").read_bytes()
            with patch("seedance_bridge.requests.post") as post:
                seedance_bridge.wait_and_finish(folder, "draft-id", status=lambda _: None)
                self.assertEqual((folder / "final-preview.mp4").read_bytes(), before)
                with self.assertRaisesRegex(ValueError, "request ID differs"):
                    seedance_bridge.wait_and_finish(folder, "unrelated-id")
                (folder / "final-preview.mp4").write_bytes(b"user changed output")
                with self.assertRaisesRegex(ValueError, "output changed"):
                    seedance_bridge.wait_and_finish(folder, "draft-id")
                self.assertEqual((folder / "final-preview.mp4").read_bytes(), b"user changed output")
                post.assert_not_called()

    def test_source_change_during_restoration_never_exports_mismatched_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'upload.mp4').write_bytes(b'original audio')
            response = Mock()
            response.json.return_value = {'status': 'COMPLETED', 'result': 'https://media.example/result.mp4'}
            def changed_restore(generated, target):
                restored(generated, target)
                (folder / 'upload.mp4').write_bytes(b'changed audio during restoration')
            with patch('seedance_bridge.setting', side_effect=settings), patch('seedance_bridge.credential', return_value='test'), patch('seedance_bridge.requests.post', return_value=response), patch('seedance_bridge.requests.get', return_value=Mock(content=b'generated')), patch('seedance_bridge.finish_preview', side_effect=changed_restore):
                with self.assertRaisesRegex(ValueError, 'changed during audio restoration'):
                    seedance_bridge.wait_and_finish(folder, 'draft-id', status=lambda _: None)
                self.assertFalse((folder / 'final-preview.mp4').exists())
                self.assertTrue((folder / 'seedance-result.mp4').exists())

    def test_export_rename_crash_is_recovered_from_ready_record(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "upload.mp4").write_bytes(b"source")
            response = Mock()
            response.json.return_value = {"status": "COMPLETED", "result": "https://media.example/result.mp4"}
            def fail_after_export(path, record):
                if Path(path).name == '.collection.json' and record.get('state') == 'completed':
                    raise OSError('simulated process failure after export rename')
                atomic_json(path, record)
            with patch("seedance_bridge.setting", side_effect=settings), patch("seedance_bridge.credential", return_value="test"), patch("seedance_bridge.requests.post", return_value=response) as post, patch("seedance_bridge.requests.get", return_value=Mock(content=b"generated")) as download, patch("seedance_bridge.finish_preview", side_effect=restored) as finish:
                with patch('seedance_bridge.atomic_json', side_effect=fail_after_export), self.assertRaisesRegex(OSError, 'simulated process failure'):
                    seedance_bridge.wait_and_finish(folder, 'draft-id', status=lambda _: None)
                self.assertTrue((folder / 'final-preview.mp4').exists())
                self.assertEqual(json.loads((folder / '.collection.json').read_text())['state'], 'export-ready')
                seedance_bridge.wait_and_finish(folder, 'draft-id', status=lambda _: None)
                self.assertEqual(json.loads((folder / '.collection.json').read_text())['state'], 'completed')
                post.assert_called_once()
                download.assert_called_once()
                finish.assert_called_once()

    def test_download_rename_crash_preserves_video_and_resumes_without_redownload(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'upload.mp4').write_bytes(b'source')
            response = Mock()
            response.json.return_value = {'status': 'COMPLETED', 'result': 'https://media.example/result.mp4'}
            real_replace = seedance_bridge.os.replace
            def fail_after_download(source, target):
                real_replace(source, target)
                if Path(target).name == 'seedance-result.mp4':
                    raise OSError('simulated process failure after download rename')
            with patch('seedance_bridge.setting', side_effect=settings), patch('seedance_bridge.credential', return_value='test'), patch('seedance_bridge.requests.post', return_value=response) as post, patch('seedance_bridge.requests.get', return_value=Mock(content=b'generated')) as download, patch('seedance_bridge.finish_preview', side_effect=restored) as finish:
                with patch('seedance_bridge.os.replace', side_effect=fail_after_download), self.assertRaisesRegex(OSError, 'simulated process failure'):
                    seedance_bridge.wait_and_finish(folder, 'draft-id', status=lambda _: None)
                self.assertEqual((folder / 'seedance-result.mp4').read_bytes(), b'generated')
                self.assertEqual(json.loads((folder / '.collection.json').read_text())['state'], 'download-ready')
                seedance_bridge.wait_and_finish(folder, 'draft-id', status=lambda _: None)
                self.assertTrue((folder / 'final-preview.mp4').exists())
                post.assert_called_once()
                download.assert_called_once()
                finish.assert_called_once()


if __name__ == "__main__":
    unittest.main()
