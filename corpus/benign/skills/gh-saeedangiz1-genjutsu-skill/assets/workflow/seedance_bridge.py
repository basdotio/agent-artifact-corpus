"""Durable Seedance draft/HD submission and restart-safe output collection."""
from pathlib import Path
import concurrent.futures
import hashlib
import json
import os
import shutil
import tempfile
import time

import requests

from config import credential, setting
from media_host import upload
from audio_workflow import finish_preview
from job_state import atomic_json, durable_submit, job_lock, load_submission

DRAFT_STAGE = 'seedance-draft'
HD_STAGE = 'seedance-hd'


def _hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _base():
    return setting('ENHANCOR_BASE_URL', 'https://apireq.enhancor.ai/api/seedance2.5/v1').rstrip('/') + '/'


def _request_id(response):
    ident = response.get('requestId') if isinstance(response, dict) else None
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError('Enhancor did not return a request ID; reconcile its acceptance before retrying.')
    return ident


def _reference(path, secondary=False):
    from preflight import inspect_reference
    report = inspect_reference(path, secondary=secondary)
    return {'sha256': report['sha256'], 'type': report['type']}


def _draft_identity(folder, prompt, sirio, tein, base):
    from mask_review import fingerprint
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError('A nonempty generation prompt is required.')
    return {
        'contract': 2,
        'reviewed_input': fingerprint(folder),
        'source_sha256': _hash(folder / 'upload.mp4'),
        'prompt': prompt,
        'references': [_reference(sirio)] + ([_reference(tein, secondary=True)] if tein else []),
        'endpoint': base,
    }


def _queue(base, key, payload):
    response = requests.post(base + 'queue', headers={'x-api-key': key}, json=payload, timeout=90)
    response.raise_for_status()
    data = response.json()
    _request_id(data)
    return data


def _save_draft(folder, response, payload, identity):
    ident = _request_id(response)
    atomic_json(folder / 'seedance-response.json', response)
    atomic_json(folder / 'generation.json', {
        'request_id': ident,
        'prompt': payload['prompt'],
        'video': 'seedance-result.mp4',
        'mode': payload['mode'],
        'source_sha256': identity['source_sha256'],
        'reviewed_input': identity['reviewed_input'],
    })
    return ident


def _omni_timing(folder, prepared):
    """Check integer provider duration against actual source audio before hosting."""
    import av
    from preflight import omni_duration
    with av.open(str(prepared)) as video, av.open(str(folder / 'upload.mp4')) as original:
        if video.duration is None or original.duration is None or not video.streams.video:
            raise ValueError('Omni routing requires readable prepared and original container durations.')
        duration = omni_duration(float(video.duration / av.time_base), float(original.duration / av.time_base))
        stream = video.streams.video[0]
        ratio = stream.width / stream.height
    ratios = {'16:9': 16/9, '9:16': 9/16, '1:1': 1, '4:3': 4/3, '3:4': 3/4, '21:9': 21/9}
    return duration, min(ratios, key=lambda r: abs(ratios[r] - ratio))


def submit(folder, prompt, sirio, tein=None, status=print):
    folder = Path(folder)
    with job_lock(folder):
        from mask_review import require_approved, is_mesh, _mode
        # Never rebuild prepared input after approval: upload exactly the reviewed file.
        require_approved(folder)
        base = _base()
        identity = _draft_identity(folder, prompt, sirio, tein, base)
        previous = load_submission(folder, DRAFT_STAGE, identity)
        if previous is not None:
            payload = json.loads((folder / 'seedance-request.json').read_text(encoding='utf-8'))
            ident = _save_draft(folder, previous, payload, identity)
            status('Resuming accepted Seedance draft: ' + ident)
            return ident
        if (folder / 'seedance-response.json').exists():
            raise ValueError('This job already has a provider response. Resume its saved request ID; use a new job for a deliberate variation.')
        prepared = folder / 'seedance-input.mp4'
        omni = _omni_timing(folder, prepared) if identity['references'][0]['type'] == 'video' else None
        key = credential('ENHANCOR_API_KEY')
        webhook = setting('ENHANCOR_WEBHOOK_URL')
        if not webhook:
            raise ValueError('Webhook URL required. Start the local tunnel or set ENHANCOR_WEBHOOK_URL.')
        status('Uploading the reviewed video with embedded vocals and character references')
        references = [Path(sirio)] + ([Path(tein)] if tein else [])
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            urls = list(pool.map(upload, [prepared] + references))
        payload = {
            'resolution': '1080p', 'output_format': 'mp4', 'pass_faces': True,
            'webhook_url': webhook, 'mode': 'edit', 'is_draft': True,
            'aspect_ratio': 'adaptive', 'videos': [urls[0]], 'audios': [],
            'images': urls[1:],
            'prompt': prompt.replace('@Audio1', 'the audio embedded in @Video1') +
                '\n@Video1 contains the colored-depth composite and embedded isolated vocals pitched up three semitones, without the music bed; use its embedded audio for performance and lip synchronization. ' +
                ('@Image1 is the primary character reference; @Image2 is the secondary character reference.' if tein else '@Image1 is the only replacement character reference.'),
        }
        if omni is not None:
            duration, aspect_ratio = omni
            payload.update(mode='multi_reference', duration=str(duration), aspect_ratio=aspect_ratio)
            payload['videos'] = [urls[0], urls[1]]
            payload['images'] = urls[2:]
            payload['prompt'] = prompt.replace('@Audio1', 'the audio embedded in @Video1') + '\n@Video1 is the source edit and contains isolated vocals pitched +3 semitones. @Video2 is only the primary character visual identity reference. Use only @Video1 audio for speech timing.'
            if tein:
                payload['prompt'] += ' @Image1 is the secondary character visual identity reference.'
        if is_mesh(folder):
            description = 'depth composite with face mesh overlay' if _mode(folder) == 'depth_mesh' else 'original video with face mesh overlay'
            payload['prompt'] = payload['prompt'].replace('colored-depth composite', description) + ' Remove all face mesh lines and any depth colors from the output; use them only for expression and lip motion guidance. Replace the entire original identity including hair. Preserve the exact embedded dialogue and timing.'
        # Detect outside file edits during upload before any billed request is sent.
        require_approved(folder)
        if _draft_identity(folder, prompt, sirio, tein, base) != identity:
            raise ValueError('The reviewed input or character references changed during upload. Review the latest artifacts before submitting.')
        atomic_json(folder / 'seedance-request.json', payload)
        response = durable_submit(folder, DRAFT_STAGE, payload, lambda: _queue(base, key, payload), identity)
        ident = _save_draft(folder, response, payload, identity)
        status('Seedance draft submitted: ' + ident)
        return ident


def _atomic_copy(source, target):
    target = Path(target)
    fd, temporary = tempfile.mkstemp(prefix='.' + target.name + '-', suffix='.tmp', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as output, Path(source).open('rb') as original:
            shutil.copyfileobj(original, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def submit_hd(folder):
    """Complete the accepted draft with the current configured callback URL."""
    folder = Path(folder)
    with job_lock(folder):
        generation = json.loads((folder / 'generation.json').read_text(encoding='utf-8'))
        original = json.loads((folder / 'seedance-request.json').read_text(encoding='utf-8'))
        if not original.get('is_draft') or not (folder / 'final-preview.mp4').is_file():
            raise ValueError('A completed draft is required before generating 1080p.')
        source_hash = _hash(folder / 'upload.mp4')
        if generation.get('source_sha256', source_hash) != source_hash:
            raise ValueError('The original source changed after draft submission. Use a new job.')
        identity = {'draft_id': generation['request_id'], 'source_sha256': source_hash, 'draft_sha256': _hash(folder / 'final-preview.mp4'), 'endpoint': _base()}
        hd = folder / 'hd'
        hd.mkdir(exist_ok=True)
        with job_lock(hd):
            previous = load_submission(hd, HD_STAGE, identity)
            if previous is not None:
                ident = _request_id(previous)
                atomic_json(hd / 'response.json', previous)
                atomic_json(hd / 'generation.json', {'request_id': ident, 'mode': 'hd', 'source_sha256': source_hash, 'draft_id': generation['request_id']})
                return ident
            if (hd / 'response.json').exists():
                raise ValueError('HD already has a provider response. Resume its saved request ID.')
            webhook = setting('ENHANCOR_WEBHOOK_URL')
            if not webhook:
                raise ValueError('A current webhook URL is required for HD submission. Start the local tunnel or configure ENHANCOR_WEBHOOK_URL.')
            payload = {'draft_id': generation['request_id'], 'webhook_url': webhook}
            key = credential('ENHANCOR_API_KEY')
            source = hd / 'upload.mp4'
            if source.exists() and _hash(source) != source_hash:
                raise ValueError('HD source audio differs from the original draft source. Use a new job.')
            if not source.exists():
                _atomic_copy(folder / 'upload.mp4', source)
            if _hash(folder / 'upload.mp4') != source_hash or _hash(source) != source_hash or _hash(folder / 'final-preview.mp4') != identity['draft_sha256']:
                raise ValueError('The original source or accepted draft changed during HD preparation. Use a new job.')
            atomic_json(hd / 'request.json', payload)
            response = durable_submit(hd, HD_STAGE, payload, lambda: _queue(identity['endpoint'], key, payload), identity)
            atomic_json(hd / 'response.json', response)
            ident = _request_id(response)
            atomic_json(hd / 'generation.json', {'request_id': ident, 'mode': 'hd', 'source_sha256': source_hash, 'draft_id': generation['request_id']})
            return ident


def _collection_identity(folder, request_id):
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError('A saved provider request ID is required for collection.')
    source = folder / 'upload.mp4'
    if not source.is_file():
        raise ValueError('The original source is required before restoring provider output.')
    source_hash = _hash(source)
    generation_path = folder / 'generation.json'
    if generation_path.exists():
        generation = json.loads(generation_path.read_text(encoding='utf-8'))
        if generation.get('request_id') != request_id:
            raise ValueError('Collection request ID differs from this job\'s saved generation.')
        if generation.get('source_sha256', source_hash) != source_hash:
            raise ValueError('The original source changed after generation; refusing to restore different audio.')
    for name in ('seedance-response.json', 'response.json'):
        response = folder / name
        if response.exists() and _request_id(json.loads(response.read_text(encoding='utf-8'))) != request_id:
            raise ValueError('Collection request ID differs from the saved provider response.')
    return {'request_id': request_id, 'source_sha256': source_hash}


def _download(url, target, record, record_path):
    response = requests.get(url, timeout=180)
    response.raise_for_status()
    if not isinstance(response.content, bytes) or not response.content:
        raise ValueError('Provider returned an empty result video.')
    fd, temporary = tempfile.mkstemp(prefix='.seedance-download-', suffix='.mp4', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(response.content)
            output.flush()
            os.fsync(output.fileno())
        record.update(state='download-ready', download_sha256=_hash(temporary))
        atomic_json(record_path, record)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _restore_atomic(folder, generated, record, record_path):
    """A failed remux leaves existing exports intact and never exposes partial MP4."""
    stage = Path(tempfile.mkdtemp(prefix='.finish-', dir=folder))
    try:
        try:
            os.link(folder / 'upload.mp4', stage / 'upload.mp4')
        except OSError:
            shutil.copyfile(folder / 'upload.mp4', stage / 'upload.mp4')
        finish_preview(generated, stage)
        if _hash(folder / 'upload.mp4') != record['source_sha256'] or _hash(generated) != record['download_sha256']:
            raise ValueError('The source or provider video changed during audio restoration; preserving the saved input instead of exporting mismatched media.')
        exported = stage / 'final-preview.mp4'
        if not exported.is_file() or not exported.stat().st_size:
            raise ValueError('Audio restoration did not produce a complete preview.')
        with exported.open('r+b') as output:
            os.fsync(output.fileno())
        record.update(state='export-ready', output_sha256=_hash(exported))
        atomic_json(record_path, record)
        os.replace(exported, folder / 'final-preview.mp4')
        adjustment = stage / 'duration-adjustment.json'
        if adjustment.exists():
            atomic_json(folder / 'duration-adjustment.json', json.loads(adjustment.read_text(encoding='utf-8')))
        record['state'] = 'completed'
        atomic_json(record_path, record)
    finally:
        shutil.rmtree(stage)


def wait_and_finish(folder, request_id, status=print):
    """Poll an existing ID only; serialize collectors and retain completed outputs."""
    folder = Path(folder)
    with job_lock(folder):
        identity = _collection_identity(folder, request_id)
        record_path = folder / '.collection.json'
        record = json.loads(record_path.read_text(encoding='utf-8')) if record_path.exists() else dict(identity, state='pending')
        if any(record.get(key) != value for key, value in identity.items()):
            raise ValueError('This collection belongs to a different request or source. Use its saved request ID and original source.')
        preview = folder / 'final-preview.mp4'
        if preview.exists():
            if not preview.stat().st_size:
                raise ValueError('An empty saved preview exists; preserve and inspect it before collecting.')
            if record.get('output_sha256') and record['output_sha256'] != _hash(preview):
                raise ValueError('Saved output changed; preserving it instead of overwriting it.')
            if record_path.exists() and record.get('state') not in ('export-ready', 'completed'):
                raise ValueError('An untracked preview already exists; preserving it instead of overwriting it.')
            record.update(state='completed', output_sha256=_hash(preview))
            atomic_json(record_path, record)
            status('Saved final preview preserved')
            return
        if record.get('state') == 'completed':
            raise ValueError('Saved completed output is missing; restore it from backup before retrying collection.')
        generated = folder / 'seedance-result.mp4'
        if generated.exists():
            if not record.get('download_sha256') or _hash(generated) != record['download_sha256']:
                raise ValueError('An untracked or changed provider video exists; preserving it instead of overwriting it.')
            status('Restoring entire original source audio from saved provider video')
            _restore_atomic(folder, generated, record, record_path)
            return
        atomic_json(record_path, record)
        key = credential('ENHANCOR_API_KEY')
        for _ in range(360):
            response = requests.post(_base() + 'status', headers={'x-api-key': key}, json={'request_id': request_id}, timeout=30)
            response.raise_for_status()
            data = response.json()
            atomic_json(folder / 'provider-status.json', data)
            if data.get('status') == 'COMPLETED':
                url = data.get('result')
                if not isinstance(url, str) or not url.startswith('https://'):
                    raise ValueError('Seedance result URL missing.')
                _download(url, generated, record, record_path)
                record.update(state='downloaded', download_sha256=_hash(generated))
                atomic_json(record_path, record)
                status('Restoring entire original source audio; discarding generated audio')
                _restore_atomic(folder, generated, record, record_path)
                return
            if data.get('status') in ('FAILED', 'CANCELED'):
                record.update(state='provider-failed', provider_status=data.get('status'))
                atomic_json(record_path, record)
                raise RuntimeError('Seedance failed: ' + str(data.get('error') or data.get('status')))
            time.sleep(10)
        raise TimeoutError('Seedance is still pending. Request ID saved; resume collection instead of resubmitting.')
