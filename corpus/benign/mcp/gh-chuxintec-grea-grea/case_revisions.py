"""Versioned, append-only candidate identities over project-local case records.

Hashes establish file identity; roles, platforms and run IDs remain explicit
reviewer declarations. This module never runs the inspected game or test suite.
"""
from grea.host.paths import Path
import uuid

from .common import GreaError, digest, now, write_new
from .case_hashing import hash_file, audit_hashes, audit_report
from .safe_paths import relative_name
from .workflows import required_dimensions


def identity(project, path):
    value = hash_file(path)
    try:
        value['project_relative'] = Path(value['path']).relative_to(project).as_posix()
    except ValueError:
        value['project_relative'] = None
    return value


def resolve(project, value):
    relative = value.get('project_relative')
    if relative is None:
        return Path(value['path'])
    return project / relative_name(relative)


def check_file(project, value, code):
    actual = hash_file(resolve(project, value))
    if actual['sha256'] != value['sha256']:
        raise GreaError(code, 'Bound file changed; preserve the old revision and start a new one.')


def snapshot(root, selections, max_bytes=8 * 1024**3, max_files=100000):
    root = Path(root).expanduser().absolute()
    if any(p.is_symlink() for p in (root,*root.parents)):
        raise GreaError('INVALID_CANDIDATE','Candidate path components may not be links.')
    root = root.resolve()
    if not root.is_dir():
        raise GreaError('INVALID_CANDIDATE', 'Candidate root must be an existing directory.')
    if not selections or len(selections) != len(set(selections)):
        raise GreaError('INVALID_CANDIDATE', 'Select unique relative files or directories.')
    files = {}
    total = 0
    for selected in selections:
        path = root / relative_name(selected)
        if not path.exists() or any(p.is_symlink() for p in (path, *path.parents)):
            raise GreaError('INVALID_CANDIDATE', 'Missing or linked candidate selection.')
        paths = [path] if path.is_file() else sorted(path.rglob('*'))
        for file in paths:
            if file.is_symlink():
                raise GreaError('INVALID_CANDIDATE', 'Candidate links are not followed.')
            if file.is_dir():
                continue
            name = file.relative_to(root).as_posix()
            if name in files:
                continue
            if len(files) >= max_files or file.stat().st_size > max_bytes - total:
                raise GreaError('RESOURCE_LIMIT', 'Candidate exceeds the declared snapshot budget.')
            value = hash_file(file)
            total += value['bytes']
            files[name] = {k: value[k] for k in ('bytes', 'sha256')}
    if not files:
        raise GreaError('INSUFFICIENT_COVERAGE', 'Candidate selection contains no files.')
    return dict(files=dict(sorted(files.items())), sha256=digest(files), bytes=total)


def revisions(root):
    from .cases import read_record
    directory = root / 'revisions'
    if directory.is_symlink():
        raise GreaError('INVALID_CASE', 'Revision directory may not be a link.')
    return sorted((read_record(p, 'rev_') for p in directory.glob('*.json')),
                  key=lambda value: (value['order_ns'], value['id']))


def active(root, revision_id=None):
    records = revisions(root)
    if revision_id:
        match = next((value for value in records if value['id'] == revision_id), None)
        if match is None:
            raise GreaError('REVISION_NOT_FOUND', 'Select a revision in this case.')
        return match
    return records[-1] if records else None


def check_revision(root, case, revision):
    if revision is None:
        check_file(root.parent, case['source'], 'STALE_SOURCE')
        return
    if revision['case_id'] != case['case_id']:
        raise GreaError('WRONG_CASE', 'Revision belongs to another case.')
    check_file(root.parent, revision['source'], 'STALE_SOURCE')
    candidate = revision['candidate']
    directory = root.parent / candidate['project_relative'] if candidate['project_relative'] is not None else Path(candidate['root'])
    actual = snapshot(directory, candidate['selections'])
    if actual['sha256'] != candidate['sha256']:
        raise GreaError('STALE_CANDIDATE', 'Selected candidate files changed; start a new revision.',
                        details={'revision_id': revision['id'], 'expected': candidate['sha256'], 'actual': actual['sha256']})
    if revision['build_manifest']:
        check_file(root.parent, revision['build_manifest'], 'STALE_BUILD')


def start(case_dir, candidate_root, candidate_files, platform, qa_profile, build_manifest=None,
          build_id=None, source=None, mode=None, required_dimensions_override=None):
    from .cases import locate, locked, load_case, next_order
    root = locate(case_dir)
    with locked(root):
        case = load_case(root)
        selected_source = identity(root.parent, source) if source else case['source']
        if source is None:
            check_file(root.parent, selected_source, 'STALE_SOURCE')
        candidate_path = Path(candidate_root).expanduser()
        if any(p.is_symlink() for p in (candidate_path,*candidate_path.absolute().parents)):
            raise GreaError('INVALID_CANDIDATE', 'Candidate root may not be a link.')
        candidate_path = candidate_path.resolve()
        content = snapshot(candidate_path, candidate_files)
        try:
            relative = candidate_path.relative_to(root.parent).as_posix()
        except ValueError:
            relative = None
        if bool(build_manifest) != bool(build_id):
            raise GreaError('INVALID_BUILD', 'Build manifest and build_id must be supplied together.')
        task = dict(case.get('task', {}), intent=mode or case['mode'])
        dims = required_dimensions_override or (case['required_dimensions'] if mode is None else required_dimensions(mode, task.get('source_engine', 'unknown')))
        mandatory = required_dimensions(task['intent'], task.get('source_engine', 'unknown'))
        if 'native' in mandatory and 'native' not in dims:
            raise GreaError('REQUIRED_DIMENSION', 'Cross-engine native acceptance cannot be removed.')
        value = dict(schema_version=2, case_id=case['case_id'], source=selected_source, task=task,
                     required_dimensions=dims, candidate=dict(content, root=str(candidate_path), project_relative=relative, selections=candidate_files),
                     build_manifest=identity(root.parent, build_manifest) if build_manifest else None,
                     build_id=build_id, platform=platform, qa_profile=qa_profile,
                     created_at=now(), order_ns=next_order(root, 'revisions', 'rev_'), nonce=uuid.uuid4().hex)
        value['id'] = 'rev_' + digest(value)
        (root / 'revisions').mkdir(exist_ok=True)
        write_new(root / 'revisions' / (value['id'] + '.json'), value)
    return dict(revision=value, acceptance='not_run', limitations=['Only explicit candidate selections are covered; source/build/platform declarations are not attestation.'])


def read_evidence(root, case, evidence_id, verify=True):
    from .cases import read_record
    if not evidence_id.startswith('ev_') or len(evidence_id) != 67 or any(c not in '0123456789abcdef' for c in evidence_id[3:]):
        raise GreaError('INVALID_EVIDENCE_REFERENCE', 'Expected an evidence identity.')
    path = root / 'evidence' / (evidence_id + '.json')
    if not path.is_file():
        raise GreaError('INVALID_EVIDENCE_REFERENCE', 'Evidence record does not exist.')
    value = read_record(path, 'ev_')
    if value['case_id'] != case['case_id']:
        raise GreaError('WRONG_CASE', 'Evidence belongs to another case.')
    if verify:
        check_file(root.parent, value['artifact'], 'STALE_EVIDENCE')
    return value


def add(case_dir, kind, path, description, revision_id=None, run_instance=None):
    from .cases import locate, locked, load_case
    root = locate(case_dir)
    with locked(root):
        case = load_case(root)
        revision = active(root, revision_id)
        source = revision['source'] if revision else case['source']
        check_file(root.parent, source, 'STALE_SOURCE')
        path = Path(path).expanduser().absolute()
        if root == path.resolve() or root in path.resolve().parents:
            raise GreaError('INVALID_EVIDENCE', 'Artifacts must be outside case metadata.')
        value = dict(case_id=case['case_id'], kind=kind, artifact=identity(root.parent, path),
                     description=description, authority='caller_declared_role', created_at=now(), nonce=uuid.uuid4().hex,
                     revision_id=revision['id'] if revision else None, run_instance=run_instance, source_sha256=source['sha256'])
        value['id'] = 'ev_' + digest(value)
        write_new(root / 'evidence' / (value['id'] + '.json'), value)
    return dict(evidence=value, limitations=['Role and run instance are declarations, not executed gameplay. Only the new artifact was hashed.'])


def validate_claim(root, case, revision, dimension, status, evidence_ids):
    from .cases import required_kinds
    if len(evidence_ids) != len(set(evidence_ids)):
        raise GreaError('INVALID_EVIDENCE_REFERENCE', 'Evidence IDs must be unique.')
    selected = [read_evidence(root, case, key) for key in evidence_ids]
    if status != 'passed':
        return selected
    mode = revision['task']['intent'] if revision else case['mode']
    roles = {value['kind'] for value in selected}
    if not required_kinds(mode, dimension) <= roles:
        raise GreaError('INSUFFICIENT_EVIDENCE', 'Passed claim lacks required evidence roles.')
    if revision is None and mode not in ('evidence', 'assess', 'maintain'):
        raise GreaError('MISSING_CANDIDATE_REVISION', 'Create a candidate revision before accepting gameplay claims.')
    source_sha = (revision['source'] if revision else case['source'])['sha256']
    for value in selected:
        if value.get('source_sha256') != source_sha:
            raise GreaError('WRONG_SOURCE_EVIDENCE', 'Evidence belongs to another original source.')
        if value['kind'] not in ('original_static', 'original_runtime', 'approved_design') and value.get('revision_id') != (revision['id'] if revision else None):
            raise GreaError('WRONG_REVISION_EVIDENCE', 'Candidate evidence belongs to another revision.')
    if dimension in ('runtime', 'visual', 'platform'):
        runtime = [value for value in selected if value['kind'] == 'candidate_runtime']
        if not runtime or any(not value.get('run_instance') for value in runtime):
            raise GreaError('MISSING_RUN_INSTANCE', 'Runtime evidence needs an explicit observed run instance.')
    if dimension == 'platform' and (revision is None or revision['build_manifest'] is None):
        raise GreaError('MISSING_BUILD', 'Platform acceptance requires a bound build manifest.')
    return selected


def record(case_dir, dimension, status, evidence_ids, note, revision_id=None):
    from .cases import locate, locked, load_case, next_order
    root = locate(case_dir)
    with locked(root):
        case = load_case(root)
        revision = active(root, revision_id)
        check_revision(root, case, revision)
        dims = revision['required_dimensions'] if revision else case['required_dimensions']
        if dimension in dims and status == 'not_applicable':
            raise GreaError('REQUIRED_DIMENSION', 'Cannot exempt an already-required dimension.')
        validate_claim(root, case, revision, dimension, status, evidence_ids)
        value = dict(case_id=case['case_id'], revision_id=revision['id'] if revision else None,
                     dimension=dimension, status=status, evidence_ids=evidence_ids, note=note,
                     created_at=now(), order_ns=next_order(root, 'verifications', 'vr_'), nonce=uuid.uuid4().hex, authority='reviewer_assertion')
        value['id'] = 'vr_' + digest(value)
        write_new(root / 'verifications' / (value['id'] + '.json'), value)
    return dict(verification=value, executed_tests=False)


def _status(case_dir, revision_id=None):
    from .cases import locate, locked, load_case, read_record
    root = locate(case_dir)
    with locked(root, write=False):
        case = load_case(root)
        revision = active(root, revision_id)
        check_revision(root, case, revision)
        selected_id = revision['id'] if revision else None
        for name in ('evidence', 'verifications'):
            if (root / name).is_symlink():
                raise GreaError('INVALID_CASE', 'Metadata directory may not be a symlink.')
        evidence_count = 0
        for path in sorted((root / 'evidence').glob('*.json')):
            value = read_record(path, 'ev_')
            if value.get('revision_id') == selected_id:
                read_evidence(root, case, value['id'])
                evidence_count += 1
        history = sorted((read_record(path, 'vr_') for path in (root / 'verifications').glob('*.json')),
                         key=lambda value: (value['order_ns'], value['id']))
        latest = {}
        for value in history:
            if value['case_id'] != case['case_id']:
                raise GreaError('WRONG_CASE', 'Verification belongs to another case.')
            if value.get('revision_id') != selected_id:
                continue
            validate_claim(root, case, revision, value['dimension'], value['status'], value['evidence_ids'])
            latest[value['dimension']] = value
        dims = revision['required_dimensions'] if revision else case['required_dimensions']
        verdicts = {dim: latest.get(dim, dict(status='not_run', evidence_ids=[])) for dim in dims}
        missing = [dim for dim, verdict in verdicts.items() if verdict['status'] != 'passed']
        return dict(case_id=case['case_id'], revision_id=selected_id, revision_count=len(revisions(root)),
                    source_integrity='matched', candidate_integrity='matched' if revision else 'unbound',
                    evidence_count=evidence_count, dimensions=verdicts, missing_or_failed=missing,
                    declared_acceptance='ready_for_review' if not missing else 'incomplete', verified_game_equivalence=False,
                    history_count=len(history), hash_coverage='active_revision_files_and_referenced_evidence',
                    applies_to={key: revision[key] for key in ('id','build_id','platform','qa_profile')} if revision else None,
                    limitations=['Declarations do not prove executed gameplay. Other revisions remain history; they are not automatically accepted for this candidate.'])


def status(case_dir, revision_id=None, max_hash_bytes=8*1024**3):
    with audit_hashes(max_hash_bytes) as audit:
        result = _status(case_dir, revision_id)
        result['hash_audit'] = audit_report(audit)
        return result
