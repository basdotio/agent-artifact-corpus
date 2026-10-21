#!/usr/bin/env python3
"""Read-only Unity asset ledger: snapshot, compare, check-plan, verify-moves.

Python 3.9+, standard library. Never moves/deletes/imports assets or rewrites meta.
Exit 0: no issues, unchanged, clean preflight, or planned files match (verify-moves).
Exit 1: report contains changes/issues requiring review. Exit 2: invalid input/I/O.
"""
import argparse
import collections
import hashlib
import json
import os
from pathlib import PurePosixPath
from grea.host.paths import Path
import re
import sys
import unicodedata
from grea.tools._artifact_common import directory, inventory, validate_output, write_report

SCHEMA = 'unity-asset-ledger-v1'
GUID = re.compile(r'^guid:\s*([0-9a-fA-F]{32})\s*$', re.M)
CACHE = {'.DS_Store', 'Thumbs.db', 'desktop.ini'}
LIMITS = ['No Unity import, dependency closure, subasset fileID or runtime-name validation.',
          'No unused-asset or encryption verdict. Naming candidates are not rename instructions.',
          'Per-file hash checks are not an atomic filesystem snapshot; recheck before mutation.']

def key(path):
    return unicodedata.normalize('NFC', path).casefold()

def relative(path):
    if not isinstance(path, str) or not path or '\\' in path:
        raise ValueError('Expected a normalized Assets-relative POSIX path')
    value = PurePosixPath(path)
    if value.is_absolute() or any(p in ('..', '.') for p in path.split('/')) or value.as_posix() != path:
        raise ValueError('Unsafe or non-normalized path: ' + path)
    if any(ord(c) < 32 for c in path):
        raise ValueError('Control character in path')
    return path

def collisions(paths):
    groups = collections.defaultdict(list)
    for path in paths:
        groups[key(path)].append(path)
    return [values for values in groups.values() if len(values) > 1]

def snapshot(root):
    root = directory(root)
    files = inventory(root)
    excluded = sorted(p for p in files if PurePosixPath(p).name in CACHE)
    actual_files = [p for p in files if p not in excluded and not p.endswith('.meta')]
    folders = []
    for base, dirs, _ in os.walk(root, followlinks=False):
        for name in sorted(dirs):
            path = Path(base) / name
            if path.is_symlink():
                raise ValueError('Symlink refused: ' + str(path))
            folders.append(path.relative_to(root).as_posix())
    assets = {}; issues = []; naming = []
    for path in sorted(actual_files + folders):
        kind = 'file' if path in files else 'folder'
        row = {'kind': kind, 'guid': None, 'meta_sha256': None}
        if kind == 'file':
            row.update(files[path])
            row['extension'] = PurePosixPath(path).suffix.lower()
            stem = PurePosixPath(path).stem
            if re.fullmatch(r'[0-9a-fA-F]{24,}', stem):
                naming.append({'path': path, 'reason': 'hash-like-stem-review-context'})
            if '\ufffd' in path or any(ord(c) < 32 for c in path):
                naming.append({'path': path, 'reason': 'replacement-or-control-character'})
        meta = path + '.meta'
        if meta not in files:
            issues.append({'kind': 'missing_meta', 'path': path})
        else:
            if files[meta]['bytes'] > 8 * 1024 * 1024:
                raise ValueError('Meta exceeds 8 MiB limit: ' + meta)
            raw = (root / meta).read_bytes()
            if hashlib.sha256(raw).hexdigest() != files[meta]['sha256']:
                raise ValueError('Meta changed during scan: ' + meta)
            row['meta_sha256'] = files[meta]['sha256']
            try:
                matches = GUID.findall(raw.decode('utf-8-sig'))
            except UnicodeError:
                matches = []
            if len(matches) != 1 or int(matches[0], 16) == 0:
                issues.append({'kind': 'invalid_meta_guid', 'path': path})
            else:
                row['guid'] = matches[0].lower()
        assets[path] = row
    for path in files:
        if path.endswith('.meta') and path[:-5] not in assets:
            issues.append({'kind': 'orphan_meta', 'path': path})
    groups = collections.defaultdict(list)
    for path, row in assets.items():
        if row['guid']: groups[row['guid']].append(path)
    for guid, paths in groups.items():
        if len(paths) > 1: issues.append({'kind': 'duplicate_guid', 'guid': guid, 'paths': sorted(paths)})
    for paths in collisions(assets):
        issues.append({'kind': 'portable_path_collision', 'paths': paths})
    populated = {parent.as_posix() for f in actual_files for parent in PurePosixPath(f).parents}
    empty = sorted(p for p in folders if p not in populated)
    return {'schema': SCHEMA, 'assets_root': str(root), 'assets': assets, 'issues': issues,
            'empty_folders': empty, 'naming_candidates': naming, 'excluded_os_files': excluded,
            'limits': LIMITS}

def read_snapshot(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file(): raise ValueError('Expected regular snapshot file')
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict): raise ValueError('Snapshot must be an object')
    if data.get('schema') != SCHEMA or not isinstance(data.get('assets'), dict) or not isinstance(data.get('issues'), list):
        raise ValueError('Unsupported or malformed snapshot')
    for path, row in data['assets'].items():
        relative(path)
        if not isinstance(row, dict) or row.get('kind') not in ('file', 'folder'):
            raise ValueError('Invalid asset record: ' + path)
        guid = row.get('guid')
        if guid is not None and (not isinstance(guid, str) or not re.fullmatch('[0-9a-f]{32}', guid)):
            raise ValueError('Invalid GUID: ' + path)
        if row['kind'] == 'file' and (not isinstance(row.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', row['sha256'])):
            raise ValueError('Missing/invalid content hash: ' + path)
    return data

def identity_index(data):
    rows = {}
    for path, row in data['assets'].items():
        guid = row['guid']
        if not guid: continue
        if guid in rows: raise ValueError('Duplicate GUID cannot be compared: ' + guid)
        rows[guid] = (path, row)
    return rows

def compare(before, after):
    left, right = identity_index(before), identity_index(after)
    moved = []; content = []; meta = []; kinds = []
    for guid in sorted(left.keys() & right.keys()):
        old, a = left[guid]; new, b = right[guid]
        identity = {'guid': guid, 'before': old, 'after': new}
        if old != new: moved.append(identity)
        if a['kind'] != b['kind']: kinds.append(identity)
        if a.get('sha256') != b.get('sha256'): content.append(identity)
        if a.get('meta_sha256') != b.get('meta_sha256'): meta.append(identity)
    removed = [{'guid': g, 'path': left[g][0], 'kind': left[g][1]['kind']} for g in sorted(left.keys() - right.keys())]
    added = [{'guid': g, 'path': right[g][0], 'kind': right[g][1]['kind']} for g in sorted(right.keys() - left.keys())]
    replaced = [{'path': p, 'before': before['assets'][p]['guid'], 'after': after['assets'][p]['guid']}
                for p in sorted(before['assets'].keys() & after['assets'].keys())
                if before['assets'][p]['guid'] != after['assets'][p]['guid']]
    unidentified_before = [p for p, row in before['assets'].items() if not row['guid']]
    unidentified_after = [p for p, row in after['assets'].items() if not row['guid']]
    changed = bool(unidentified_before or unidentified_after or moved or content or meta or kinds or removed or added or replaced or before['issues'] or after['issues'])
    return {'schema': SCHEMA, 'operation': 'compare', 'status': 'changes_or_issues' if changed else 'unchanged',
            'moved': moved, 'removed': removed, 'added': added, 'content_changed': content,
            'meta_changed': meta, 'kind_changed': kinds, 'same_path_guid_changed': replaced,
            'before_issues': before['issues'], 'after_issues': after['issues'],
            'unidentified_before': unidentified_before, 'unidentified_after': unidentified_after,
            'limits': LIMITS + ['A reported removal is not verified archival/deletion approval; reconcile with the reviewed plan and backup hashes.']}

def windows_name(path):
    for part in PurePosixPath(path).parts:
        if re.search(r'[<>:"|?*]', part) or part.endswith((' ', '.')):
            return False
        if re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]|CONIN\$|CONOUT\$)', part.split('.')[0], re.I):
            return False
    return True

def check_plan(data, plan):
    if not isinstance(plan, dict): raise ValueError('Plan must be an object')
    if plan.get('schema') != 'unity-file-move-plan-v1' or not isinstance(plan.get('moves'), list) or not isinstance(plan.get('retire', []), list):
        raise ValueError('Expected unity-file-move-plan-v1 with moves and optional retire arrays')
    assets = data['assets']; problems = []; sources = set(); targets = []; folded = {key(p): p for p in assets}
    if data['issues']: problems.append({'kind': 'snapshot_has_issues', 'count': len(data['issues'])})
    def check_source(row, field):
        source = relative(row[field]); guid = row['guid']
        if source in sources: problems.append({'kind': 'source_reused', 'path': source})
        sources.add(source)
        if source not in assets or assets[source]['kind'] != 'file':
            problems.append({'kind': 'source_not_a_file', 'path': source})
        elif not guid or assets[source]['guid'] != guid:
            problems.append({'kind': 'source_guid_mismatch', 'path': source})
        return source
    for row in plan['moves']:
        source = check_source(row, 'from'); target = relative(row['to']); targets.append(target)
        if not windows_name(target): problems.append({'kind': 'nonportable_target_name', 'path': target})
        if key(target) in folded:
            problems.append({'kind': 'occupied_target_requires_staging', 'path': target, 'existing': folded[key(target)]})
        for parent in PurePosixPath(target).parents:
            existing = folded.get(key(parent.as_posix()))
            if existing and assets[existing]['kind'] == 'file':
                problems.append({'kind': 'target_parent_is_file', 'path': target, 'parent': existing})
    for paths in collisions(targets): problems.append({'kind': 'duplicate_target', 'paths': paths})
    target_index = {key(p): p for p in targets}
    for child in targets:
        for parent in PurePosixPath(child).parents:
            target = target_index.get(key(parent.as_posix()))
            if target:
                problems.append({'kind': 'planned_target_is_parent_file', 'path': target, 'child': child})
    for row in plan.get('retire', []):
        source = check_source(row, 'path')
        if not isinstance(row.get('reason'), str) or not row['reason'].strip():
            problems.append({'kind': 'retirement_reason_missing', 'path': source})
    return {'schema': SCHEMA, 'operation': 'check-plan', 'status': 'needs_review' if problems else 'static_preflight_clean',
            'move_count': len(plan['moves']), 'retire_count': len(plan.get('retire', [])), 'issues': problems,
            'limits': LIMITS + ['Files only. Folder moves need separate Editor planning. Occupied targets, swaps and case-only renames require explicit intermediate staging.',
                                'No dependency/root audit or authorization is inferred from static_preflight_clean.']}

def resources_key(path):
    parts = PurePosixPath(path).parts
    if 'Resources' not in parts:
        return None
    if parts.count('Resources') != 1:
        raise ValueError('Nested Resources directories need manual review: ' + path)
    tail = PurePosixPath(*parts[parts.index('Resources') + 1:])
    return tail.with_suffix('').as_posix()


def verify_moves(before, after, plan):
    """Verify only declared file moves; unrelated changes remain in compare()."""
    preflight = check_plan(before, plan)
    if not plan['moves'] or plan.get('retire'):
        raise ValueError('verify-moves requires nonempty file moves and no retire entries')
    issues = list(preflight['issues'])
    if after['issues']:
        issues.append({'kind': 'after_snapshot_has_issues', 'count': len(after['issues'])})
    identity_index(after)  # Reject duplicate GUIDs instead of choosing one.
    matched = 0
    for move in plan['moves']:
        source, target, guid = move['from'], move['to'], move['guid']
        old = before['assets'].get(source)
        new = after['assets'].get(target)
        failures = []
        if not old or not new or old.get('kind') != 'file' or new.get('kind') != 'file':
            failures.append('source_or_target_not_file')
        else:
            if old['guid'] != guid or new['guid'] != guid:
                failures.append('guid_mismatch')
            for field in ('sha256', 'meta_sha256'):
                value = old.get(field)
                if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
                    failures.append('missing_baseline_' + field)
                elif value != new.get(field):
                    failures.append(field + '_changed')
        if source in after['assets']:
            failures.append('old_path_still_present')
        if resources_key(source) != resources_key(target):
            failures.append('resources_key_changed')
        if failures:
            issues.append({'kind': 'planned_move_mismatch', 'from': source, 'to': target,
                           'guid': guid, 'failures': failures})
        else:
            matched += 1
    return {'schema': SCHEMA, 'operation': 'verify-moves',
            'status': 'needs_review' if issues else 'planned_files_match',
            'move_count': len(plan['moves']), 'matched_files': matched, 'issues': issues,
            'limits': LIMITS + [
                'Only planned FILE moves are verified. Run compare separately for all other changes and folder retirement.',
                'Resources path preservation does not prove typed loading, Addressables, object names or subasset IDs.',
                'Uses saved snapshots; it does not rehash live files or execute a migration.']}


def compare_editor(before, after):
    """Compare saved Editor identities, separate from filesystem GUID snapshots."""
    from grea.data_io import sha,encode
    def index(document):
        if document.get('schema_version')!=1 or document.get('status')!='editor_observed' or not isinstance(document.get('asset_objects'),list) or not document['asset_objects']:
            raise ValueError('Nonempty versioned Editor observation required')
        result={}
        if len(document['asset_objects'])>100000: raise ValueError('Object budget exceeded')
        for row in document['asset_objects']:
            if not isinstance(row,dict) or not re.fullmatch('[0-9a-f]{32}',row.get('guid','')) or type(row.get('local_id')) is not int:
                raise ValueError('Invalid GUID/local fileID identity')
            identity=row['guid']+':'+str(row['local_id'])
            # Multiple paths must not silently alias one object identity.
            if identity in result: raise ValueError('Duplicate Editor object identity')
            if not all(isinstance(row.get(k),str) for k in ('path','type','name')) or not isinstance(row.get('dependencies'),list): raise ValueError('Incomplete Editor observation')
            result[identity]=row
        return result
    left,right=index(before),index(after); changed=[]
    for identity in sorted(left.keys()&right.keys()):
        fields=[f for f in ('path','type','name','sprite_geometry','dependencies') if left[identity].get(f)!=right[identity].get(f)]
        if fields: changed.append(dict(identity=identity,fields=fields,before=left[identity],after=right[identity]))
    added=sorted(right.keys()-left.keys());removed=sorted(left.keys()-right.keys())
    issues=before.get('issues',[])+after.get('issues',[])
    return dict(schema=SCHEMA,operation='compare-editor',status='changes_or_issues' if changed or added or removed or issues else 'unchanged',changed=changed,added=added,removed=removed,issues=issues,
                before_sha256=sha(encode(before)),after_sha256=sha(encode(after)),limits=['Saved Editor observations only; compare filesystem snapshots separately. All changes require review; no movement or runtime correctness verdict.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    snap = sub.add_parser('snapshot'); snap.add_argument('--assets', type=Path, required=True)
    cmp = sub.add_parser('compare'); cmp.add_argument('--before', type=Path, required=True); cmp.add_argument('--after', type=Path, required=True)
    editor = sub.add_parser('compare-editor'); editor.add_argument('--before',type=Path,required=True);editor.add_argument('--after',type=Path,required=True)
    plan = sub.add_parser('check-plan'); plan.add_argument('--snapshot', type=Path, required=True); plan.add_argument('--plan', type=Path, required=True)
    verify = sub.add_parser('verify-moves'); verify.add_argument('--before', type=Path, required=True); verify.add_argument('--after', type=Path, required=True); verify.add_argument('--plan', type=Path, required=True)
    for item in (snap, cmp, plan, verify, editor): item.add_argument('--output', type=Path, required=True, help='New report; existing parent required; source evidence is never overwritten')
    args = parser.parse_args()
    try:
        if args.command == 'compare-editor':
            from grea.data_io import load
            before,_=load(args.before);after,_=load(args.after)
            sources=(args.before,args.after);validate_output(args.output,sources)
            report=compare_editor(before,after);needs_review=report['status']!='unchanged'
        elif args.command == 'snapshot':
            root = directory(args.assets); sources = (root,); validate_output(args.output, sources); report = snapshot(root)
            needs_review = bool(report['issues'])
        elif args.command == 'compare':
            before, after = read_snapshot(args.before), read_snapshot(args.after)
            sources = (args.before, args.after, Path(before['assets_root']), Path(after['assets_root'])); validate_output(args.output, sources)
            report = compare(before, after); needs_review = report['status'] != 'unchanged'
        elif args.command == 'verify-moves':
            before, after = read_snapshot(args.before), read_snapshot(args.after)
            if args.plan.is_symlink() or not args.plan.is_file(): raise ValueError('Expected regular plan file')
            sources = (args.before, args.after, args.plan, Path(before['assets_root']), Path(after['assets_root']))
            validate_output(args.output, sources)
            report = verify_moves(before, after, json.loads(args.plan.read_text(encoding='utf-8')))
            needs_review = bool(report['issues'])
        else:
            data = read_snapshot(args.snapshot)
            if args.plan.is_symlink() or not args.plan.is_file(): raise ValueError('Expected regular plan file')
            sources = (args.snapshot, args.plan, Path(data['assets_root'])); validate_output(args.output, sources)
            report = check_plan(data, json.loads(args.plan.read_text(encoding='utf-8'))); needs_review = bool(report['issues'])
        write_report(report, args.output, sources)
        print(json.dumps({'report': str(args.output), 'status': 'needs_review' if needs_review else 'static_check_complete'}))
        return 1 if needs_review else 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr); return 2
if __name__ == '__main__': sys.exit(main())
