"""Deterministic local gates. No provider calls, uploads, or automatic conversion."""
from pathlib import Path
import hashlib
import importlib
import io
import math
import shutil
import subprocess
import sys

MAX_SECONDS = 30.0
MODES = {'depth', 'face_mesh', 'depth_mesh'}
PROVIDERS = {'replicate', 'replicate-chenxwh', 'huggingface'}
IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp'}
VIDEO_SUFFIXES = {'.mp4', '.mov', '.webm'}
ROOT = Path(__file__).resolve().parent


def file_identity(path):
    path = Path(path)
    if not path.is_file() or not path.stat().st_size:
        raise ValueError('Media must be an existing, nonempty file.')
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for part in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(part)
    return {'sha256': digest.hexdigest(), 'bytes': path.stat().st_size}


def _duration(stream, container):
    if stream.duration is not None and stream.time_base is not None:
        return float(stream.duration * stream.time_base)
    return float(container.duration / 1_000_000) if container.duration is not None else None


def _check_duration(seconds):
    if seconds is not None and (not math.isfinite(seconds) or seconds <= 0):
        raise ValueError('Media duration is invalid.')
    if seconds is not None and seconds > MAX_SECONDS:
        raise ValueError('Use a clip of 30 seconds or less; shortening it requires a new source file.')


def _mp4_packet_probe(path):
    """Test source codecs with actual compressed packets, without transcoding."""
    import av
    buffer = io.BytesIO()
    try:
        with av.open(str(path)) as inp, av.open(buffer, 'w', format='mp4') as out:
            streams = [inp.streams.video[0], inp.streams.audio[0]]
            targets = {s.index: out.add_stream_from_template(s) for s in streams}
            counts = {s.index: 0 for s in streams}
            for packet in inp.demux(streams):
                if packet.dts is None or counts[packet.stream.index] >= 32:
                    continue
                original_index = packet.stream.index
                packet.stream = targets[original_index]
                out.mux(packet)
                counts[original_index] += 1
                if all(count >= 32 for count in counts.values()):
                    break
            if not all(counts.values()):
                raise ValueError('Source streams have no usable compressed packets.')
        buffer.seek(0)
        with av.open(buffer) as muxed:
            if not muxed.streams.video or not muxed.streams.audio:
                raise ValueError('MP4 packet probe lost a source stream.')
    except Exception as exc:
        raise ValueError('Source codecs cannot be copied into MP4. Supply a compatible source; original audio will not be silently transcoded.') from exc


def _inspect_video(path, require_audio=True, packet_probe=True):
    import av
    import numpy as np
    path = Path(path).resolve()
    identity = file_identity(path)
    try:
        with av.open(str(path)) as container:
            if not container.streams.video:
                raise ValueError('Source has no video stream.')
            video = container.streams.video[0]
            container_seconds = float(container.duration / av.time_base) if container.duration is not None else None
            video_seconds = _duration(video, container)
            _check_duration(container_seconds)
            _check_duration(video_seconds)
            count = 0
            decoded_end = 0.0
            first_time = None
            previous_time = None
            rate = float(video.average_rate or video.guessed_rate or 0)
            if not math.isfinite(rate) or rate <= 0:
                raise ValueError('Video has no usable frame rate.')
            for frame in container.decode(video=0):
                if frame.width <= 0 or frame.height <= 0 or not frame.to_ndarray(format='rgb24').size:
                    raise ValueError('Video contains an undecodable or empty frame.')
                if frame.time is None or not math.isfinite(float(frame.time)):
                    raise ValueError('Video frames have missing or invalid timestamps; supply a timestamped source.')
                current_time = float(frame.time)
                if previous_time is not None and current_time < previous_time:
                    raise ValueError('Video frame timestamps move backwards; supply a correctly timed source.')
                previous_time = current_time
                first_time = current_time if first_time is None else first_time
                elapsed = current_time - first_time
                if elapsed > MAX_SECONDS + 1e-6:
                    raise ValueError('Decoded video exceeds 30 seconds.')
                decoded_end = max(decoded_end, elapsed + 1 / rate)
                count += 1
                if count / rate > MAX_SECONDS + 1 / rate + 1e-6:
                    raise ValueError('Decoded video exceeds 30 seconds.')
            if count == 0:
                raise ValueError('Source has no decodable video frames.')
            decoded_seconds = max(decoded_end, count / rate)
            # Frame quantization may extend a container boundary by one frame.
            seconds = video_seconds or container_seconds or decoded_seconds
            _check_duration(seconds)
            report = {'path': str(path), **identity, 'duration': seconds, 'video_codec': video.codec_context.name,
                      'width': video.width, 'height': video.height, 'fps': rate, 'frames': count,
                      'decoded_video_duration': decoded_seconds, 'container_duration': container_seconds}
        if require_audio:
            with av.open(str(path)) as container:
                if not container.streams.audio:
                    raise ValueError('Source has no audio track; this workflow requires original speech or song.')
                audio = container.streams.audio[0]
                audio_seconds = _duration(audio, container)
                _check_duration(audio_seconds)
                samples = 0
                audible = False
                decoded_audio_seconds = 0.0
                largest_audio_frame_seconds = 0.0
                for frame in container.decode(audio=0):
                    if frame.samples <= 0 or not frame.sample_rate:
                        raise ValueError('Audio contains empty or invalid samples.')
                    values = frame.to_ndarray()
                    if not values.size or not np.isfinite(values).all():
                        raise ValueError('Source audio cannot be decoded into finite samples.')
                    audible = audible or bool(np.any(values != 0))
                    samples += frame.samples
                    decoded_audio_seconds += frame.samples / frame.sample_rate
                    largest_audio_frame_seconds = max(largest_audio_frame_seconds, frame.samples / frame.sample_rate)
                if samples == 0 or not audible:
                    raise ValueError('Source audio is empty or entirely silent; provide audible speech or song.')
                # Compressed codecs can decode one trailing padded frame beyond the declared end.
                if decoded_audio_seconds > MAX_SECONDS + largest_audio_frame_seconds + 1e-6:
                    raise ValueError('Decoded audio exceeds 30 seconds.')
                report.update(audio_codec=audio.codec_context.name, audio_samples=samples,
                              audio_rate=audio.codec_context.sample_rate,
                              decoded_audio_duration=decoded_audio_seconds)
            if packet_probe:
                _mp4_packet_probe(path)
                report['original_mp4_packet_copy'] = True
            if audio_seconds is not None and abs(seconds-audio_seconds) > .25:
                raise ValueError('Original video and audio durations differ by more than 0.25 seconds; supply an aligned source before hosted work.')
        return report
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('Media could not be fully decoded locally: ' + type(exc).__name__) from exc


def inspect_source(path):
    """Return a JSON-serializable report or fail before any hosted work."""
    return _inspect_video(path)


def inspect_reference(path, secondary=False):
    path = Path(path).resolve()
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        from PIL import Image
        identity = file_identity(path)
        try:
            with Image.open(path) as image:
                if image.format not in {'JPEG', 'PNG', 'WEBP'}:
                    raise ValueError('Reference content must be JPEG, PNG, or WebP.')
                image.load()
                if image.width <= 0 or image.height <= 0:
                    raise ValueError('Reference image is empty.')
                return {'path': str(path), **identity, 'type': 'image', 'width': image.width, 'height': image.height, 'format': image.format}
        except (OSError, SyntaxError) as exc:
            raise ValueError('Reference image cannot be decoded.') from exc
    if suffix in VIDEO_SUFFIXES and not secondary:
        report = _inspect_video(path, require_audio=False, packet_probe=False)
        report['type'] = 'video'
        return report
    raise ValueError('Secondary references must be JPEG, PNG, or WebP images.' if secondary else
                     'Reference must be a JPEG, PNG, WebP image or MP4, MOV, WebM video.')


def mesh_python(root=ROOT):
    from platform_runtime import mesh_python as resolve
    return resolve(root)


def _mesh_ready(root=ROOT):
    root = Path(root)
    python = mesh_python(root)
    model = root / 'models' / 'face_landmarker.task'
    if not model.is_file() or not model.stat().st_size or not (root / 'mesh_worker.py').is_file():
        raise ValueError('Face mesh model or worker is missing. Complete face-mesh setup before hosted work.')
    check = ('import sys; assert sys.version_info >= (3,12); import av,numpy,PIL,mediapipe as mp; '
             'options=mp.tasks.vision.FaceLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=sys.argv[1])); '
             'detector=mp.tasks.vision.FaceLandmarker.create_from_options(options); detector.close()')
    try:
        result = subprocess.run([str(python), '-c', check, str(model)], capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError('Face mesh worker failed its local dependency/model check.') from exc
    if result.returncode:
        raise ValueError('Face mesh worker needs Python 3.12+ and usable av/numpy/Pillow/MediaPipe dependencies and model.')
    return str(python)


def _encoding_ready():
    """Exercise the local codecs before Demucs is billed."""
    import av
    import numpy as np
    from fractions import Fraction
    try:
        buffer = io.BytesIO()
        with av.open(buffer, 'w', format='mp4') as out:
            video = out.add_stream('libx264', rate=24)
            video.width = video.height = 16
            video.pix_fmt = 'yuv420p'
            audio = out.add_stream('aac', rate=44100)
            audio.layout = 'stereo'
            frame = av.VideoFrame.from_ndarray(np.zeros((16, 16, 3), np.uint8), format='rgb24')
            frame.pts = 0
            frame.time_base = Fraction(1, 24)
            for packet in video.encode(frame):
                out.mux(packet)
            for packet in video.encode():
                out.mux(packet)
            sound = av.AudioFrame.from_ndarray(np.zeros((2, 2048), np.float32), format='fltp', layout='stereo')
            sound.sample_rate = 44100
            sound.pts = 0
            for packet in audio.encode(sound):
                out.mux(packet)
            for packet in audio.encode():
                out.mux(packet)
        with av.open(io.BytesIO(), 'w', format='wav') as out:
            pcm = out.add_stream('pcm_s16le', rate=44100)
            pcm.layout = 'stereo'
            for packet in pcm.encode(sound):
                out.mux(packet)
            for packet in pcm.encode():
                out.mux(packet)
    except Exception as exc:
        raise ValueError('Local H.264/AAC/WAV encoding is unavailable; fix the PyAV/FFmpeg installation before hosted work.') from exc


def omni_duration(prepared_seconds, original_seconds=None):
    """Validate the integer Omni duration against unchanged original audio.

    Final export accepts at most 0.25 seconds of extra generated video. A
    generated shortfall up to 0.5 seconds is supported by the existing recorded
    final-frame hold; no source audio is trimmed, looped, or stretched.
    """
    try:
        prepared_seconds = float(prepared_seconds)
        original_seconds = prepared_seconds if original_seconds is None else float(original_seconds)
    except (TypeError, ValueError) as exc:
        raise ValueError('Omni timing requires finite, positive source and prepared durations.') from exc
    _check_duration(prepared_seconds)
    _check_duration(original_seconds)
    duration = max(4, min(30, round(prepared_seconds)))
    surplus = duration - original_seconds
    if surplus > .25 or surplus < -.5:
        raise ValueError(
            f'Omni video-reference timing is incompatible: {original_seconds:.3f}s of original audio '
            f'would queue {duration}s of generated video. Supply a compatible source or use an image '
            'reference; audio will not be trimmed, looped, or stretched.'
        )
    return duration


def preflight_job(source, mode='depth', provider='replicate', reference=None, second_reference=None,
                  require_dependencies=True, require_rubberband=True):
    if mode not in MODES or provider not in PROVIDERS:
        raise ValueError('Unsupported workflow mode or depth provider.')
    report = {'source': inspect_source(source), 'mode': mode, 'provider': provider}
    if reference is not None:
        report['reference'] = inspect_reference(reference)
        if report['reference']['type'] == 'video':
            projected_seconds = max(1, round(report['source']['duration'] * 24)) / 24
            original_seconds = report['source']['container_duration'] or report['source']['duration']
            report['omni_duration_seconds'] = omni_duration(projected_seconds, original_seconds)
    if second_reference is not None:
        report['second_reference'] = inspect_reference(second_reference, secondary=True)
    if require_dependencies:
        if sys.version_info < (3, 12):
            raise ValueError('Preparation requires Python 3.12 or newer.')
        dependencies = ['av', 'numpy', 'PIL', 'requests']
        if mode in {'depth', 'depth_mesh'}:
            dependencies.append('scipy')
            if provider == 'huggingface':
                dependencies.append('gradio_client')
        for name in dependencies:
            try:
                importlib.import_module(name)
            except Exception as exc:
                raise ValueError('Preparation dependency unavailable: ' + name) from exc
        _encoding_ready()
        from config import credential
        credential('REPLICATE_API_TOKEN')  # Demucs is required in every mode.
        if mode in {'face_mesh', 'depth_mesh'}:
            report['mesh_python'] = _mesh_ready()
    if require_rubberband:
        binary = shutil.which('rubberband')
        if not binary:
            raise ValueError('Rubber Band is required for preparation. Install it before hosted work; media inspection alone does not require it.')
        try:
            available = subprocess.run([binary, '--version'], capture_output=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError('Rubber Band cannot run locally. Fix it before hosted work.') from exc
        if available.returncode:
            raise ValueError('Rubber Band failed its local version check. Fix it before hosted work.')
    report['dependencies_checked'] = require_dependencies
    return report


def bind_preparation(folder, report, prompt='person'):
    """Bind partial preparation to one source and recipe; never reuse another job."""
    import json
    from job_state import atomic_json
    folder = Path(folder)
    if any((folder / name).exists() for name in ('generation.json', '.submission-seedance-draft.json')):
        raise ValueError('Generation was already submitted or attempted. Resume that generation; prepare a new job for changed inputs.')
    identity = {'source': {key: report['source'][key] for key in ('sha256', 'bytes')},
                'mode': report['mode'], 'provider': report['provider'], 'prompt': prompt,
                'recipe': 'genjutsu-24fps-960px-v1'}
    saved = folder / 'preparation-state.json'
    if saved.exists():
        previous = json.loads(saved.read_text())
        if previous.get('identity') != identity:
            raise ValueError('Source or preparation settings changed. Create a new job instead of reusing previous paid predictions or review artifacts.')
    else:
        # Older folders cannot prove that their partial artifacts belong to this source.
        if any((folder / name).exists() for name in ('audio-manifest.json', 'audio-prediction.json', 'depth-raw.mp4', 'sam-raw-request.json')):
            raise ValueError('Existing preparation has no source identity. Create a fresh job; legacy artifacts cannot be reused safely.')
        atomic_json(saved, {'identity': identity, 'state': 'preparing'})
    source = Path(report['source']['path'])
    if file_identity(source) != identity['source']:
        raise ValueError('Source changed during local inspection. Inspect and prepare a fresh job.')
    upload = folder / 'upload.mp4'
    if upload.exists():
        if file_identity(upload) != identity['source']:
            raise ValueError('Saved source differs from this preparation. Create a new job.')
    else:
        shutil.copy2(source, upload)
        if file_identity(upload) != identity['source']:
            raise ValueError('Source changed during copying. Create a new job.')
    atomic_json(folder / 'workflow-mode.json', {'mode': report['mode'], 'provider': report['provider'], 'subject': prompt})
    return identity


def main(argv=None):
    import argparse
    import json
    import sysconfig
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('--mode', choices=sorted(MODES), default='depth')
    parser.add_argument('--provider', choices=sorted(PROVIDERS), default='replicate')
    parser.add_argument('--reference')
    parser.add_argument('--second-reference')
    parser.add_argument('--dependencies', action='store_true', help='Also require Python, provider credentials, Rubber Band and optional mesh worker.')
    args = parser.parse_args(argv)
    if sysconfig.get_config_var('Py_GIL_DISABLED'):
        parser.exit(1,'Preflight needs regular CPython 3.12+; free-threaded Python cannot load these compiled video wheels.\n')
    try:
        report = preflight_job(args.source, args.mode, args.provider, args.reference, args.second_reference,
                               require_dependencies=args.dependencies, require_rubberband=args.dependencies)
    except (ValueError, RuntimeError, ImportError) as exc:
        parser.exit(1, 'Preflight failed: ' + str(exc) + '\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
