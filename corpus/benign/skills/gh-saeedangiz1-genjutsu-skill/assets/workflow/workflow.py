"""Agent CLI; local IDs survive restarts and inputs retain the caller's paths."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import uuid

from config import ROOT, load_env
from platform_runtime import mesh_python

MODES = ['depth', 'face_mesh', 'depth_mesh']
PROVIDERS = ['replicate', 'replicate-chenxwh', 'huggingface']


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('prepare')
    c.add_argument('video')
    c.add_argument('--subject', default='person')
    c.add_argument('--provider', default='replicate', choices=PROVIDERS)
    c.add_argument('--mode', choices=MODES, default='depth')
    for command in ['status', 'repair-rgb', 'resume', 'resume-preparation', 'hd', 'review', 'submit']:
        c = sub.add_parser(command)
        c.add_argument('job')
        if command == 'review':
            c.add_argument('--approve', action='store_true')
            c.add_argument('--fingerprint', required=True)
            c.add_argument('--note', required=True)
        if command == 'submit':
            c.add_argument('--prompt-file', required=True)
            c.add_argument('--reference', required=True)
            c.add_argument('--second-reference')
        if command == 'resume':
            c.add_argument('--hd', action='store_true')
        if command == 'resume-preparation':
            c.add_argument('--mode', choices=MODES)
            c.add_argument('--subject')
            c.add_argument('--provider', choices=PROVIDERS)
    return p


def _editable(folder):
    if (folder / 'generation.json').exists() or (folder / '.submission-seedance-draft.json').exists():
        raise ValueError('This job already has a generation/submission intent. Resume collection; use a new job for changed preparation.')


def _preparation_status(folder, state, message, **details):
    from job_state import atomic_json
    atomic_json(folder / 'status.json', dict(id=folder.name, state=state, status=message, **details))


def prepare_folder(folder, mode, subject, provider):
    from job_state import job_lock
    _editable(folder)

    def progress(message):
        # Preparation runners call progress while holding the job lock.
        print(message, flush=True)
        _preparation_status(folder, 'running', message)

    try:
        if mode == 'face_mesh':
            from face_mesh import run as run_mesh
            run_mesh(folder / 'upload.mp4', folder, status=progress)
        elif mode == 'depth_mesh':
            from face_mesh import run_depth
            run_depth(folder / 'upload.mp4', folder, subject, provider, status=progress)
        else:
            from pipeline import run
            run(folder / 'upload.mp4', folder, subject, provider, status=progress)
    except BaseException as exc:
        # Fail-fast lock collisions must not overwrite the active owner's status.
        try:
            with job_lock(folder):
                state = 'interrupted' if isinstance(exc, (KeyboardInterrupt, SystemExit)) else 'error'
                _preparation_status(folder, state, 'Preparation stopped; inspect the error and resume this saved job.', error_type=type(exc).__name__)
        except (ValueError, OSError):
            pass
        raise
    with job_lock(folder):
        _preparation_status(folder, 'done', 'Preparation complete · full input review required')


def resume_preparation(folder, args):
    context_path = folder / 'workflow-mode.json'
    manifest_path = folder / 'manifest.json'
    context = json.loads(context_path.read_text(encoding='utf-8')) if context_path.exists() else {}
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    mode = args.mode or context.get('mode', manifest.get('mode', 'depth'))
    subject = args.subject or context.get('subject', manifest.get('prompt', 'person'))
    provider = args.provider or context.get('provider', manifest.get('depth_provider', 'replicate'))
    if mode not in MODES or provider not in PROVIDERS:
        raise ValueError('Saved preparation mode/provider is invalid; inspect workflow-mode.json.')
    if not (folder / 'upload.mp4').is_file():
        raise ValueError('Saved source upload.mp4 is missing. Restore the exact original source before resuming.')
    print('JOB:', folder.name, flush=True)
    prepare_folder(folder, mode, subject, provider)


def repair_rgb(folder):
    from job_state import job_lock, atomic_json
    from raw_masks import segment_raw, clean_border_fragments
    from pipeline import composite
    from audio_workflow import prepare_seedance_video
    with job_lock(folder):
        _editable(folder)
        mode = json.loads((folder / 'workflow-mode.json').read_text()).get('mode') if (folder / 'workflow-mode.json').exists() else 'depth'
        if mode == 'face_mesh':
            raise ValueError('Fast face mesh has no SAM mask. Resume facial preparation instead.')
        # Fail before segmentation if the combined-mode worker/model is unavailable.
        if mode == 'depth_mesh':
            worker = mesh_python(ROOT)
            with (ROOT / 'models' / 'face_landmarker.task').open('rb') as model:
                if len(model.read(16)) != 16:
                    raise ValueError('Face mesh model is incomplete; run bash setup-face-mesh.sh.')
        meta = json.loads((folder / 'manifest.json').read_text())
        repair = folder / 'rgb-repair'
        repair.mkdir(exist_ok=True)
        masks = clean_border_fragments(segment_raw(folder / 'original.mp4', repair, meta.get('prompt', 'person')))
        composite(folder / 'original.mp4', folder / 'depth.mp4', masks, folder, folder / 'upload.mp4')
        if mode == 'depth_mesh':
            import subprocess
            shutil.copy2(folder / 'composite-silent.mp4', folder / 'depth-composite-silent.mp4')
            subprocess.run([str(worker), str(ROOT / 'mesh_worker.py'), str(folder), '--depth'], check=True)
        prepare_seedance_video(folder)
        (folder / 'mask-review.json').unlink(missing_ok=True)
        meta['mask_method'] = 'SAM 3 on original RGB, preserving depth colors'
        atomic_json(folder / 'manifest.json', meta)
        print('Repaired. Review the entire clip again; approval cleared.')


def main(argv=None):
    load_env()
    p = parser()
    args = p.parse_args(argv)
    if args.command == 'prepare':
        from job_state import atomic_json
        folder = ROOT / 'runs' / uuid.uuid4().hex
        folder.mkdir(parents=True)
        print('JOB:', folder.name, flush=True)
        atomic_json(folder / 'workflow-mode.json', {'mode': args.mode, 'provider': args.provider, 'subject': args.subject})
        source = Path(args.video).expanduser().resolve()
        try:
            shutil.copy2(source, folder / 'upload.mp4')
        except OSError as exc:
            _preparation_status(folder, 'error', 'Cannot save source; restore the source and resume this job.', error_type=type(exc).__name__)
            raise
        prepare_folder(folder, args.mode, args.subject, args.provider)
        return 0
    if len(args.job) != 32 or any(c not in '0123456789abcdef' for c in args.job):
        p.error('Expected a 32-character local job ID')
    folder = ROOT / 'runs' / args.job
    if not folder.is_dir():
        p.error('Job does not exist')
    if args.command == 'resume-preparation':
        resume_preparation(folder, args)
    elif args.command == 'status':
        from mask_review import state
        print(json.dumps({'mask_review': state(folder),
                          'preparation': json.loads((folder / 'status.json').read_text()) if (folder / 'status.json').exists() else None,
                          'generation': json.loads((folder / 'generation.json').read_text()) if (folder / 'generation.json').exists() else None}, indent=2))
    elif args.command == 'review':
        from mask_review import review
        print(review(folder, args.approve, args.note, args.fingerprint))
    elif args.command == 'repair-rgb':
        repair_rgb(folder)
    else:
        from seedance_bridge import submit, submit_hd, wait_and_finish
        if args.command == 'submit':
            request = submit(folder, Path(args.prompt_file).read_text(encoding='utf-8'), args.reference, args.second_reference)
        elif args.command == 'hd':
            request = submit_hd(folder)
            folder = folder / 'hd'
        else:
            folder = folder / 'hd' if args.hd else folder
            saved = folder / ('response.json' if args.hd else 'seedance-response.json')
            request = json.loads(saved.read_text())['requestId']
        wait_and_finish(folder, request)
        from job_state import atomic_json
        atomic_json(folder / 'status.json', {'id': args.job, 'state': 'done', 'status': 'Final preview ready · original source audio',
                                            'final_url': f'/runs/{args.job}/' + ('hd/' if folder.name == 'hd' else '') + 'final-preview.mp4'})
        print(folder / 'final-preview.mp4')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, RuntimeError) as exc:
        print('Workflow stopped:', exc, file=sys.stderr)
        sys.exit(1)
