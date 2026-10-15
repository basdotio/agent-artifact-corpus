"""工程生成 create-only, staged Unity generation. Never edits an adopted game project."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import unicodedata
import ctypes

from jsonschema import Draft202012Validator
from .common import GreaError, digest, package_root, write_new
from . import runner, registry
from .unity_projects import Reader, relative, overlaps, strict_json, KEYWORDS
from .unity_project_contracts import PROFILE, REFERENCE, MANIFEST as MANIFEST_SCHEMA

VERSION = '0.1.1'
TEMPLATE = {'id': 'grea-minimal-2d', 'version': '0.1.0'}
MANIFEST = 'Tools/Generated/manifests/project.json'
MODULES = [{'name': 'Counter', 'layers': ['Domain', 'Gameplay', 'Presentation', 'Services']}]
LIMITS = ['Creates only a new staged project or verifies its own unchanged generated project.',
          'Adopt is read-only; refactor, template upgrades and automatic rollback/deletion are unsupported.',
          'Editor compile/binding receipt is not PlayMode, Player, physical input or game parity acceptance.',
          'Unknown or interrupted writes are preserved as recovery_required; never blindly replayed.',
          'Local trusted filesystem and cooperative lock; not a sandbox for concurrent hostile filesystem writers.']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def _reader(root, cancel=None):
    supplied = Path(root).expanduser().absolute()
    if supplied != supplied.resolve():
        raise GreaError('UNSAFE_PROJECT_ENTRY', 'Root and ancestors must not be symlinks.')
    return Reader(supplied, 10000, 134217728, cancel)


def _profile(reader, profile):
    profile = relative(profile)
    p = strict_json(reader.read(profile, json_file=True), profile)
    if list(Draft202012Validator(PROFILE).iter_errors(p)):
        raise GreaError('INVALID_PROFILE', 'Profile must satisfy the v1 schema.')
    if any(x in KEYWORDS for x in p['namespace'].split('.')):
        raise GreaError('INVALID_PROFILE', 'Reserved C# namespace identifier.')
    unity = relative(p['paths']['unityProject'])
    for key in ('evidenceRoot', 'buildRoot'):
        value = relative(p['paths'][key])
        if overlaps(value, unity) or overlaps(value, profile):
            raise GreaError('PATH_CONFLICT', 'Managed, evidence and profile paths must be separate.')
        reader.path(value)
    if overlaps(p['paths']['evidenceRoot'], p['paths']['buildRoot']) or overlaps(unity, profile):
        raise GreaError('PATH_CONFLICT', 'Overlapping configured paths.')
    if p['toolchain'] != REFERENCE['toolchain'] or p['assetBackend'] != 'catalog':
        raise GreaError('UNSUPPORTED_COMBINATION', '工程生成 supports only the locked Unity/URP/uGUI/macOS reference combination.')
    if p['template'] != TEMPLATE or p['modules'] != MODULES:
        raise GreaError('UNSUPPORTED_TEMPLATE', '工程生成 requires template 0.1.0 and the single Counter composition module.')
    if set(p['features']) != {'lifecycle', 'ui', 'resources', 'audio', 'save', 'diagnostics'} or p['frameworkPackages'] or p['exceptions']:
        raise GreaError('UNSUPPORTED_TEMPLATE', '工程生成 recipe locks all six features and bundled packages; overrides/exceptions are unsupported.')
    for name in ('saveNamespace', 'qaSaveNamespace'):
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,47}', p[name]):
            raise GreaError('INVALID_PROFILE', '工程生成 save namespaces must match the file save adapter.')
    if p['saveNamespace'].casefold() == p['qaSaveNamespace'].casefold() or any(re.fullmatch(r'(con|prn|aux|nul|com[0-9]|lpt[0-9])', p[n]) for n in ('saveNamespace','qaSaveNamespace')):
        raise GreaError('INVALID_PROFILE', 'QA namespace must differ from player namespace.')
    for path in p['scenes'].values():
        relative(path)
        if not path.startswith('Assets/Game/Scenes/') or not path.endswith('.unity'):
            raise GreaError('INVALID_PROFILE', '工程生成 scenes must be .unity assets under Assets/Game/Scenes/.')
    if p['scenes']['bootstrap'].casefold() == p['scenes']['entry'].casefold():
        raise GreaError('PATH_CONFLICT', 'Bootstrap and entry must be distinct.')
    if any(p['dependencyLock'].values()):
        raise GreaError('INVALID_PROFILE', 'New recipe uses its bundled dependency lock; profile lock hashes must be null.')
    reader.path(unity)
    return p


def _recipe(p):
    root = package_root()
    files = {}
    package_dir = root / 'tools/unity/framework/packages'
    for source in sorted(package_dir.rglob('*')):
        if source.is_symlink():
            raise GreaError('UNSAFE_TEMPLATE', 'Template contains a symlink.')
        if source.is_file():
            files['Packages/' + source.relative_to(package_dir).as_posix()] = source.read_bytes()
    sample = root / 'tools/unity/templates/counter-composition/Assets/Game'
    for source in sorted(sample.rglob('*')):
        if source.is_symlink():
            raise GreaError('UNSAFE_TEMPLATE', 'Sample contains a symlink.')
        if source.suffix in ('.cs', '.asmdef'):
            files['Assets/Game/' + source.relative_to(sample).as_posix()] = source.read_text().replace('Game.', p['namespace'] + '.').encode()
    assembly_path = 'Assets/Game/Bootstrap/Game.Bootstrap.asmdef'
    assembly = json.loads(files[assembly_path]); assembly['references'].append('Grea.Foundation.Runtime')
    files[assembly_path] = encoded(assembly)
    seed = root / 'tools/unity/templates/minimal-project/ProjectBootstrap.cs.txt'
    files['Assets/Game/Bootstrap/ProjectBootstrap.cs'] = seed.read_text().replace('__NAMESPACE__', p['namespace']).encode()
    files['Packages/manifest.json'] = encoded({'dependencies': {'com.unity.render-pipelines.universal': '17.6.0', 'com.unity.ugui': '2.6.0', 'com.unity.modules.audio': '1.0.0'}})
    # Unity resolves the same pinned built-in package graph; tests are opt-in, not player dependencies.
    lock = json.loads((root / 'tools/unity/framework/test-packages-lock.json').read_text())
    files['Packages/packages-lock.json'] = encoded(lock)
    files['ProjectSettings/ProjectVersion.txt'] = b'm_EditorVersion: 6000.6.2f1\n'
    files['.gitignore'] = b'/Library/\n/Temp/\n/Logs/\n/Obj/\n/UserSettings/\n/Build/\n*.csproj\n*.sln\n.DS_Store\n'
    for name in files:
        relative(name)
    return files


def _inventory(reader, unity):
    for directory in ('Assets', 'Packages', 'ProjectSettings', 'Tools'):
        reader.scan(unity + '/' + directory)
    if reader.path(unity + '/.gitignore').exists(): reader.read(unity + '/.gitignore')
    found = {}; names = set()
    for name, info in reader.identities.items():
        if not name.startswith(unity + '/'):
            continue
        rel = name[len(unity) + 1:]
        key = unicodedata.normalize('NFC', rel).casefold()
        if key in names:
            raise GreaError('PATH_CONFLICT', 'Case/Unicode path collision.', details={'path': rel})
        names.add(key)
        if info['kind'] == 'file':
            found[rel] = info['sha256']
    return found


def _manifest_check(reader, unity, current, recipe_id):
    raw = strict_json(reader.read(unity + '/' + MANIFEST, json_file=True), MANIFEST)
    if list(Draft202012Validator(MANIFEST_SCHEMA).iter_errors(raw)):
        raise GreaError('INVALID_MANIFEST', 'Ownership manifest schema validation failed.')
    if raw.get('generatorVersion') != VERSION or raw.get('recipeId') != recipe_id:
        raise GreaError('STALE_GENERATOR', 'Generator/template/profile changed; implicit upgrades are forbidden.')
    files = raw.get('files')
    if not isinstance(files, list) or not files:
        raise GreaError('INVALID_MANIFEST', 'Missing ownership entries.')
    conflicts, changed, known = [], [], set()
    for item in files:
        name = relative(item['path'])
        if name in known or (name != '.gitignore' and not name.startswith(('Assets/', 'Packages/', 'ProjectSettings/', 'Tools/'))):
            raise GreaError('INVALID_MANIFEST', 'Duplicate or out-of-scope ownership.')
        known.add(name)
        if item['owner'] not in ('generated', 'package', 'seed-once'):
            raise GreaError('INVALID_MANIFEST', 'Unknown owner.')
        if current.get(name) != item['sha256']:
            (changed if item['owner'] == 'seed-once' and name in current and not name.endswith('.meta') else conflicts).append(name)
    if conflicts:
        raise GreaError('OWNERSHIP_CONFLICT', 'Owned assets changed or disappeared; no writes performed.', details={'paths': conflicts[:100]})
    return raw, changed, sorted(set(current) - known - {MANIFEST})


def plan_generation(project_root, profile='grea-project.json', mode='new', cancel=None):
    reader = _reader(project_root, cancel); p = _profile(reader, profile)
    unity = p['paths']['unityProject']; files = _recipe(p)
    source = {name: sha(value) for name, value in files.items()}
    identity = digest({'generator': VERSION, 'implementation': sha(Path(__file__).read_bytes()), 'profile': p,
                       'source': source, 'provider': registry.tool('unity_cli')})
    current = _inventory(reader, unity)
    changed = []; unknown = []; manifest = None
    if mode == 'adopt':
        action = 'preserve'
    elif mode != 'new':
        raise GreaError('UNSUPPORTED_MODE', '工程生成 does not support refactor writes.')
    elif (reader.root / unity).exists():
        if MANIFEST not in current:
            raise GreaError('OWNERSHIP_CONFLICT', 'Existing targets without a generation manifest are never overwritten, including empty targets.')
        manifest, changed, unknown = _manifest_check(reader, unity, current, identity)
        action = 'verify'
    else:
        action = 'create'
    reader.recheck()
    data = {'schemaVersion': 1, 'generatorVersion': VERSION, 'template': TEMPLATE, 'recipeId': identity,
            'projectId': p['projectId'], 'target': unity, 'mode': mode, 'action': action,
            'profileSha256': sha(reader.data[profile]), 'snapshotSha256': digest(current),
            'sourceFiles': source, 'seedChanges': changed, 'humanFiles': unknown,
            'generationReady': mode == 'new', 'limitations': LIMITS,
            'requiredEditorAssets': [f'Assets/GreaGenerated/{n}' for n in ('ButtonShell.prefab', 'ModalShell.prefab', 'UIHost.prefab', 'BootstrapConfig.asset', 'Renderer.asset', 'Pipeline.asset')] + list(p['scenes'].values()),
            'ownership': {'Assets/Game': 'seed-once', 'Packages': 'package', 'Assets/GreaGenerated': 'generated', 'scenes': 'generated', 'ProjectSettings': 'generated', 'unknown': 'human'}}
    owned = {item['path']: item['owner'] for item in manifest['files']} if manifest else {}
    bindings = {'UIHost.prefab': ['canvas','pageLayer','modalLayer','toastLayer','events','openButton','modal'],
                'ModalShell.prefab': ['content','blocker','closeButton','firstSelected','events:bound-by-UIHost'],
                'ButtonShell.prefab': ['button'], 'BootstrapConfig.asset': ['entryScene','playerSaveNamespace','qaSaveNamespace']}
    names = sorted(set(source) | set(data['requiredEditorAssets'])) if action == 'create' else sorted(current)
    data['items'] = [{'action': 'create' if action == 'create' else 'preserve', 'logicalId': name,
                      'target': name, 'expectedBeforeHash': current.get(name),
                      'owner': owned.get(name, 'human' if action != 'create' else
                                         ('package' if name.startswith('Packages/') else 'seed-once' if name.startswith('Assets/Game/') and name not in data['requiredEditorAssets'] else 'generated')),
                      'preserveGuid': action != 'create' or name.endswith('.meta'),
                      'requiredBindings': bindings.get(Path(name).name, []),
                      'reason': 'New staged output only' if action == 'create' else 'Preserve existing bytes; no overwrite',
                      'validationIds': ['GEN-01','GEN-02','PFB-02']} for name in names]
    data['planId'] = digest({'root': str(reader.root), 'plan': data})
    return data


def _atomic(path, value):
    temp = path.with_name(path.name + '.next')
    if temp.exists():
        raise GreaError('RECOVERY_REQUIRED', 'Interrupted state write; preserve .next and inspect.')
    with temp.open('xb') as f:
        f.write(encoded(value)); f.flush(); os.fsync(f.fileno())
    os.replace(temp, path)


@contextlib.contextmanager
def _lock(root):
    if os.name != 'posix':
        raise GreaError('UNSUPPORTED_PLATFORM', '工程生成 mutation currently requires POSIX locking.')
    import fcntl
    fd = os.open(root / '.grea-generation.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise GreaError('GENERATION_BUSY', 'Another generation/recovery owns the root lock.')
        yield
    finally:
        os.close(fd)


def _checkpoint(stage):
    """Private deterministic interruption seam for tests; never a public input."""


def _stage_snapshot(stage):
    reader = _reader(stage)
    result = {}
    for part in ('Assets', 'Packages', 'ProjectSettings', 'Tools'):
        reader.scan(part)
    if reader.path('.gitignore').exists(): reader.read('.gitignore')
    for rel, info in reader.identities.items():
        if info['kind'] == 'file' and rel != MANIFEST:
            result[rel] = info['sha256']
    reader.recheck()
    return result


def _assert_no_editor(stage):
    # Unity's project lock is advisory. Refuse even stale locks; do not unlink them.
    if (stage / 'Temp/UnityLockfile').exists():
        raise GreaError('EDITOR_BUSY', 'Editor lock remains; verify that Editor has exited before recovery.')


from .common import publish_directory as _publish_new


def _prepare(stage, p, state, cancel):
    files = _recipe(p)
    request = {'generatorVersion': VERSION, 'identity': state['recipeId'], 'bootstrapScene': p['scenes']['bootstrap'], 'entryScene': p['scenes']['entry'],
               'bootstrapType': p['namespace'] + '.Bootstrap.ProjectBootstrap', 'playerSaveNamespace': p['saveNamespace'], 'qaSaveNamespace': p['qaSaveNamespace']}
    files['Tools/Generated/request.json'] = encoded(request)
    stage.mkdir(exist_ok=True)
    current = _stage_snapshot(stage)
    if any(n not in files or value != sha(files[n]) for n, value in current.items()):
        raise GreaError('OWNERSHIP_CONFLICT', 'Partial source staging contains changed or unowned bytes.')
    for name, data in files.items():
        if cancel is not None and cancel.is_set(): raise GreaError('CANCELLED', 'Staging cancelled; explicit recovery is available.')
        if name in current: continue
        path = stage / name; path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as f: f.write(data)
        _checkpoint('source:' + name)
    state['phase'] = 'prepared'; state['prepared'] = _stage_snapshot(stage)


def generate_project(project_root, plan_id, run_dir, profile='grea-project.json', timeout_seconds=240,
                     max_output_bytes=16777216, max_inline_bytes=32768, cancel=None):
    reader = _reader(project_root, cancel); p = _profile(reader, profile); root = reader.root
    run_dir = relative(run_dir)
    if not run_dir.startswith(p['paths']['evidenceRoot'] + '/'):
        raise GreaError('INVALID_OUTPUT', 'Run directory must be under the configured evidence root.')
    with _lock(root):
        plan = plan_generation(root, profile, cancel=cancel)
        if plan['planId'] != plan_id:
            raise GreaError('STALE_PLAN', 'Project/profile/template input changed; plan again.')
        if plan['action'] == 'verify':
            return {'state': 'unchanged', 'target': plan['target'], 'seedChanges': plan['seedChanges'],
                    'humanFiles': plan['humanFiles'], 'verification': 'prior_generated_bytes_only', 'limitations': LIMITS}
        out = reader.path(run_dir)
        if out.exists(): raise GreaError('OUTPUT_EXISTS', 'Use a fresh run directory, or explicit recovery.')
        reader.recheck(); reader.check_cancel()
        out.mkdir(parents=True)
        state = {'schemaVersion': 1, 'generatorVersion': VERSION, 'profile': profile, 'recipeId': plan['recipeId'],
                 'planId': plan_id, 'target': plan['target'], 'phase': 'preparing', 'attempts': 0, 'sourceFiles': plan['sourceFiles']}
        _atomic(out / 'state.json', state)
        _prepare(out / 'staging', p, state, cancel); _atomic(out / 'state.json', state)
        _checkpoint('prepared')
        return _advance(root, out, p, state, timeout_seconds, max_output_bytes, max_inline_bytes, cancel)


def recover_generation(project_root, run_dir, profile='grea-project.json', timeout_seconds=240,
                       max_output_bytes=16777216, max_inline_bytes=32768, cancel=None):
    reader = _reader(project_root, cancel); p = _profile(reader, profile); root = reader.root
    run_dir = relative(run_dir)
    if not run_dir.startswith(p['paths']['evidenceRoot'] + '/'):
        raise GreaError('INVALID_OUTPUT', 'Recovery must select an evidence run under this root.')
    with _lock(root):
        out = reader.path(run_dir)
        state = strict_json(reader.read(run_dir + '/state.json', json_file=True), 'state.json')
        if state.get('generatorVersion') != VERSION or state.get('profile') != profile or state.get('target') != p['paths']['unityProject']:
            raise GreaError('STALE_GENERATOR', 'Recovery identity/version mismatch.')
        plan = plan_generation(root, profile, cancel=cancel)
        if state['recipeId'] != plan['recipeId']:
            raise GreaError('STALE_PLAN', 'Recovery cannot apply changed profile/template/source inputs.')
        reader.recheck(); reader.check_cancel()
        if state['phase'] == 'preparing':
            _prepare(out / 'staging', p, state, cancel); _atomic(out / 'state.json', state)
        return _advance(root, out, p, state, timeout_seconds, max_output_bytes, max_inline_bytes, cancel)


def _advance(root, out, p, state, timeout, output_budget, inline_budget, cancel):
    target = root / state['target']; stage = out / 'staging'
    if state['phase'] == 'published':
        if not target.is_dir():
            raise GreaError('RECOVERY_REQUIRED', 'Published target is missing; no automatic recreation or success claim.')
        plan_generation(root, state['profile'], cancel=cancel)
        return {'state': 'unchanged', 'target': state['target'], 'limitations': LIMITS}
    if target.exists():
        if state['phase'] == 'verified' and not stage.exists() and sha((target / MANIFEST).read_bytes()) == state['manifestSha256']:
            current = _stage_snapshot(target)
            if current != state['verifiedFiles']: raise GreaError('OWNERSHIP_CONFLICT', 'Post-publish bytes changed; retained.')
            state['phase'] = 'published'; _atomic(out / 'state.json', state)
            return {'state': 'recovered', 'target': state['target'], 'limitations': LIMITS}
        raise GreaError('OWNERSHIP_CONFLICT', 'Target appeared during generation; retained.')
    _assert_no_editor(stage)
    if state['phase'] in ('prepared', 'editor_running'):
        if state['phase'] == 'editor_running':
            previous = out / ('editor-' + str(state['attempts'])) / 'run.json'
            if not previous.is_file():
                raise GreaError('RECOVERY_REQUIRED', 'Prior Editor attempt has no exit receipt; verify process state manually, never duplicate a possibly running Editor.')
            prior = strict_json(previous.read_bytes(), 'run.json')
            group = prior.get('process_group')
            if group and os.name == 'posix':
                try: os.killpg(group, 0)
                except ProcessLookupError: pass
                else: raise GreaError('EDITOR_BUSY', 'Prior Editor process group still exists.')
        journal_path = stage / 'Tools/Generated/editor-journal.json'
        if journal_path.exists():
            prior_journal = strict_json(journal_path.read_bytes(), 'editor-journal')
            if type(prior_journal.get('errorCount')) is not int or prior_journal['errorCount'] != 0:
                raise GreaError('RECOVERY_REQUIRED', 'Prior Editor errors or legacy journal cannot be replayed as success; preserve this attempt.')
        current = _stage_snapshot(stage)
        if state['phase'] == 'editor_running' and current != state.get('failedSnapshot'):
            raise GreaError('RECOVERY_REQUIRED', 'No matching settled failure snapshot; preserve possible concurrent/interrupted changes for review.')
        for name, value in state['prepared'].items():
            # Package manager may normalize the generated lock. Everything else is immutable input.
            if name != 'Packages/packages-lock.json' and current.get(name) != value:
                raise GreaError('OWNERSHIP_CONFLICT', 'Staged source was changed; retained.', details={'path': name})
        if state['phase'] == 'prepared' and current != state['prepared']:
            raise GreaError('OWNERSHIP_CONFLICT', 'Unrecorded staged files appeared before Editor execution.')
        state['phase'] = 'editor_running'; state['attempts'] += 1; _atomic(out / 'state.json', state)
        _checkpoint('editor_running')
        args = ['run', str(stage), '--editor-version', '6000.6.2f1', '--format', 'json', '--', '-nographics', '-logFile', '-', '-executeMethod', 'Grea.Editor.ProjectGenerator.Run']
        receipt, _, failure = runner.execute('unity_cli', args, str(out / ('editor-' + str(state['attempts']))),
                                             timeout_seconds=timeout, max_output_bytes=output_budget, max_inline_bytes=inline_budget, cancel=cancel)
        if failure or receipt['exit_code'] != 0:
            state['failedSnapshot'] = _stage_snapshot(stage); _atomic(out / 'state.json', state)
            raise GreaError('RECOVERY_REQUIRED', 'Editor did not finish. Inspect its receipt/process state; target has not been published.',
                            details={'reason': receipt.get('reason'), 'run_dir': str(out)}, next_action='Use recover_unity_generation only after the Editor has exited; never rerun generation blindly.')
        _assert_no_editor(stage)
        journal = strict_json((stage / 'Tools/Generated/editor-journal.json').read_bytes(), 'editor-journal')
        if (not journal.get('complete') or journal.get('pending') or journal.get('identity') != state['recipeId']
                or type(journal.get('errorCount')) is not int or journal['errorCount'] != 0):
            raise GreaError('VERIFICATION_FAILED', 'Editor did not produce a completed binding receipt.')
        expected = {f'Assets/GreaGenerated/{n}' for n in ('ButtonShell.prefab', 'ModalShell.prefab', 'UIHost.prefab', 'BootstrapConfig.asset', 'Renderer.asset', 'Pipeline.asset')} | set(p['scenes'].values())
        if {a['path'] for a in journal['assets']} != expected:
            raise GreaError('VERIFICATION_FAILED', 'Editor output set differs from recipe.')
        current = _stage_snapshot(stage)
        for item in journal['assets']:
            if current.get(item['path']) != item['sha256'] or current.get(item['path'] + '.meta') != item['metaSha256']:
                raise GreaError('OWNERSHIP_CONFLICT', 'Generated asset changed before publication.')
        records = []; assets = {a['path']: a for a in journal['assets']}
        for name, value in sorted(current.items()):
            owner = 'package' if name.startswith('Packages/') else ('seed-once' if name.startswith('Assets/Game/') and name.removesuffix('.meta') not in expected else 'generated')
            asset = assets.get(name, {})
            meta = current.get(name + '.meta')
            guid = re.search(rb'^guid: ([a-f0-9]{32})', (stage / (name + '.meta')).read_bytes(), re.M) if meta else None
            records.append({'path': name, 'logicalId': name, 'sha256': value, 'owner': owner, 'metaSha256': meta,
                            'guid': guid[1].decode() if guid else None, 'fileIds': asset.get('fileIds', [])})
        manifest = {'schemaVersion': 1, 'standardVersion': '1.0.0', 'generatorVersion': VERSION, 'template': TEMPLATE, 'recipeId': state['recipeId'], 'planId': state['planId'], 'projectId': p['projectId'], 'previousManifestSha256': None, 'files': records}
        Draft202012Validator(MANIFEST_SCHEMA).validate(manifest)
        (stage / MANIFEST).parent.mkdir(parents=True, exist_ok=True)
        if (stage / MANIFEST).exists():
            if (stage / MANIFEST).read_bytes() != encoded(manifest):
                raise GreaError('OWNERSHIP_CONFLICT', 'An interrupted manifest differs; retained.')
        else: write_new(stage / MANIFEST, manifest)
        state.update(phase='verified', verifiedFiles=current, manifestSha256=sha((stage / MANIFEST).read_bytes()))
        _atomic(out / 'state.json', state); _checkpoint('verified')
    if state['phase'] != 'verified':
        raise GreaError('RECOVERY_REQUIRED', 'Unknown recovery phase; no writes applied.')
    if cancel is not None and cancel.is_set(): raise GreaError('CANCELLED', 'Cancelled before publication; recover the verified run explicitly.')
    if _stage_snapshot(stage) != state['verifiedFiles'] or sha((stage / MANIFEST).read_bytes()) != state['manifestSha256']:
        raise GreaError('OWNERSHIP_CONFLICT', 'Verified staging was changed; retained.')
    # Recheck all configured paths just before atomic publication. Same filesystem is required.
    reader = _reader(root); _profile(reader, state['profile'])
    current_plan = plan_generation(root, state['profile'])
    if current_plan['planId'] != state['planId']: raise GreaError('STALE_PLAN', 'Inputs changed before publication.')
    target.parent.mkdir(parents=True, exist_ok=True)
    # rename is used only with a nonexistent destination, under a cooperative per-root lock.
    if target.exists() or target.is_symlink(): raise GreaError('OWNERSHIP_CONFLICT', 'Target appeared before publication.')
    _publish_new(stage, target); _checkpoint('published')
    state['phase'] = 'published'; _atomic(out / 'state.json', state)
    return {'state': 'generated', 'target': state['target'], 'manifest': state['target'] + '/' + MANIFEST,
            'runDir': out.relative_to(root).as_posix(), 'editorReceipt': (out.relative_to(root) / ('editor-' + str(state['attempts'])) / 'run.json').as_posix(),
            'manifestSha256': state['manifestSha256'], 'editor': 'compile_and_bindings_passed', 'playMode': 'not_run', 'player': 'not_run', 'limitations': LIMITS}
