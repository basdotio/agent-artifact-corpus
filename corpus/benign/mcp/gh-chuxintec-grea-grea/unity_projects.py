"""Bounded, read-only Unity project inspection and non-executable inspection plans."""
import hashlib
import json
import os
from pathlib import PurePosixPath
from grea.host.paths import Path
import re
import stat
import unicodedata
from collections import deque

from jsonschema import Draft202012Validator
from .common import GreaError, digest
from .unity_project_contracts import (
    PROFILE, REPORT, PLAN, REFERENCE, STANDARD_VERSION, PLANNER_VERSION, LEGACY_TEMPLATE, documents,
)

LIMITATIONS = [
    'Static filesystem observations only; no Editor, package restore, imports, code execution or project writes.',
    'This operation is read-only; use plan_unity_generation and generate_unity_project for the separate create-only recipe.',
    'GUID text and assembly references do not prove fileID bindings, dynamic loading, compilation or gameplay parity.',
    'Editor, PlayMode, Player and existing-game behavior acceptance remain not_run.',
    'Exceptions are recorded but do not suppress findings in static inspection.',
    'A supplied baseline is hashed as caller-provided evidence; its behavioral claims are not verified.',
]
KEYWORDS = set('abstract as base bool break byte case catch char checked class const continue decimal default delegate do double else enum event explicit extern false finally fixed float for foreach goto if implicit in int interface internal is lock long namespace new null object operator out override params private protected public readonly ref return sbyte sealed short sizeof stackalloc static string struct switch this throw true try typeof uint ulong unchecked unsafe ushort using virtual void volatile while'.split())
RESERVED = {'con', 'prn', 'aux', 'nul', *('com'+str(n) for n in range(1, 10)), *('lpt'+str(n) for n in range(1, 10))}


def relative(value, allow_dot=False):
    if allow_dot and value == '.':
        return value
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise GreaError('INVALID_PROJECT_PATH', 'Expected a bounded relative path.')
    parts = value.split('/')
    if any(p in ('', '.', '..') or p[-1:] in (' ', '.') or re.search(r'[\\<>:"|?*\x00-\x1f]', p)
           or p.split('.')[0].casefold() in RESERVED for p in parts):
        raise GreaError('INVALID_PROJECT_PATH', 'Path must be relative, portable and contain no traversal or reserved component.', details={'path': value})
    return value


def overlaps(a, b):
    a, b = PurePosixPath(a), PurePosixPath(b)
    return a == b or a in b.parents or b in a.parents


def strict_json(data, name):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('Duplicate JSON member')
            out[key] = value
        return out
    try:
        return json.loads(data, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Non-JSON constant')))
    except (ValueError, UnicodeError, RecursionError) as error:
        raise GreaError('INVALID_PROJECT_JSON', 'Expected strict UTF-8 JSON without duplicate keys.', details={'path': name}) from error


class Reader:
    """Never traverses symlinks, follows special files, or imports project code."""
    def __init__(self, root, max_files, max_bytes, cancel):
        supplied = Path(root).expanduser().absolute()
        if supplied.is_symlink() or (supplied.exists() and getattr(supplied.lstat(),'st_file_attributes',0)&0x400) or not supplied.is_dir():
            raise GreaError('INVALID_PROJECT_ROOT', 'Project root must be an existing non-symlink directory.')
        self.root = supplied.resolve()
        self.root_identity = (self.root.stat().st_dev, self.root.stat().st_ino)
        self.max_files, self.max_bytes, self.cancel = max_files, max_bytes, cancel
        self.data, self.identities, self.tokens, self.directories = {}, {}, {}, {}
        self.bytes = 0
        self.missing = set()

    def check_cancel(self):
        if self.cancel is not None and self.cancel.is_set():
            raise GreaError('CANCELLED', 'Read-only project inspection cancelled.')

    def path(self, rel):
        relative(rel, allow_dot=True)
        path = self.root
        for part in PurePosixPath(rel).parts:
            path /= part
            if path.is_symlink() or (path.exists() and getattr(path.lstat(),'st_file_attributes',0)&0x400):
                raise GreaError('UNSAFE_PROJECT_ENTRY', 'Symlink paths are not inspected.', details={'path': rel})
            if path.exists() and path != self.root / rel and not path.is_dir():
                raise GreaError('PATH_CONFLICT', 'A parent component is not a directory.', details={'path': rel})
        if not path.resolve().is_relative_to(self.root):
            raise GreaError('UNSAFE_PROJECT_ENTRY', 'Path escapes project root.')
        if not path.exists():
            self.missing.add(rel)
        return path

    def open_fd(self, rel, directory=False):
        """On POSIX anchor each component to an fd: an ancestor-symlink race cannot escape."""
        if os.open in os.supports_dir_fd and hasattr(os, 'O_NOFOLLOW'):
            flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_NONBLOCK', 0)
            descriptor = os.open(self.root, flags | os.O_DIRECTORY)
            try:
                current = os.fstat(descriptor)
                if (current.st_dev, current.st_ino) != self.root_identity:
                    raise GreaError('STALE_INPUT', 'Project root was replaced during inspection.')
                parts = PurePosixPath(rel).parts
                for index, part in enumerate(parts):
                    next_fd = os.open(part, flags | (os.O_DIRECTORY if directory or index < len(parts)-1 else 0), dir_fd=descriptor)
                    os.close(descriptor)
                    descriptor = next_fd
                result = descriptor
                descriptor = None
                return result
            finally:
                if descriptor is not None:
                    os.close(descriptor)
        if os.name=='nt':
            from .host.windows_files import open_fd
            return open_fd(self.path(rel))
        return os.open(self.path(rel), os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))

    @staticmethod
    def token(s):
        return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_mode)

    def read(self, rel, json_file=False):
        self.check_cancel()
        path = self.path(rel)
        if rel in self.data:
            if json_file and len(self.data[rel]) > 1048576:
                raise GreaError('RESOURCE_LIMIT', 'JSON input exceeds the parsing budget.', details={'path': rel})
            return self.data[rel]
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            raise GreaError('UNSAFE_PROJECT_ENTRY', 'Only regular files can be inspected.', details={'path': rel})
        if len(self.identities) >= self.max_files or self.bytes + before.st_size > self.max_bytes or (json_file and before.st_size > 1048576):
            raise GreaError('RESOURCE_LIMIT', 'Inspection budget exceeded; no complete plan was produced.', details={'path': rel})
        if os.name=='nt':
            from .host.windows_files import path_token,fd_token
            original=path_token(path)
        with os.fdopen(self.open_fd(rel), 'rb') as handle:
            if (fd_token(handle.fileno()) != original) if os.name=='nt' else (self.token(os.fstat(handle.fileno())) != self.token(before)):
                raise GreaError('STALE_INPUT', 'File changed before it could be inspected.', details={'path': rel})
            data = handle.read(min(before.st_size + 1, self.max_bytes - self.bytes + 1))
            after = os.fstat(handle.fileno())
            if os.name=='nt':opened=fd_token(handle.fileno())
        changed=(original!=opened or path_token(path)!=original) if os.name=='nt' else (self.token(before)!=self.token(after) or self.token(path.lstat())!=self.token(before))
        if changed or len(data)!=before.st_size:
            raise GreaError('STALE_INPUT', 'File changed during inspection.', details={'path': rel})
        self.path(rel)
        self.bytes += len(data)
        self.tokens[rel] = opened if os.name=='nt' else self.token(after)
        self.data[rel] = data
        guid = re.search(rb'^guid: ([0-9a-f]{32})\s*$', data, re.M) if rel.endswith('.meta') else None
        self.identities[rel] = {'path': rel, 'kind': 'file', 'bytes': len(data),
                                'sha256': hashlib.sha256(data).hexdigest(), 'guid': guid[1].decode() if guid else None}
        return data

    def children(self, rel):
        self.check_cancel()
        path = self.path(rel)
        if not path.is_dir():
            raise GreaError('PATH_CONFLICT', 'Expected a directory.', details={'path': rel})
        names = []
        descriptor = self.open_fd(rel, directory=True) if os.scandir in os.supports_fd else None
        try:
            with os.scandir(descriptor if descriptor is not None else path) as entries:
                for entry in entries:
                    names.append(entry.name)
                    if len(names) > self.max_files:
                        raise GreaError('RESOURCE_LIMIT', 'Directory entry budget exceeded.')
        finally:
            if descriptor is not None:
                os.close(descriptor)
        names.sort()
        self.directories[rel] = names
        return names

    def scan(self, rel):
        path = self.path(rel)
        if not path.exists():
            return
        if not path.is_dir():
            self.read(rel)
            return
        pending = [rel]
        while pending:
            current = pending.pop()
            names = self.children(current)
            if len(self.identities) >= self.max_files:
                raise GreaError('RESOURCE_LIMIT', 'Inventory entry budget exceeded.')
            self.identities[current] = {'path': current, 'kind': 'directory', 'bytes': 0, 'sha256': None, 'guid': None}
            for name in names:
                relative(name)
                child = str(PurePosixPath(current) / name)
                p = self.path(child)
                if p.is_dir():
                    pending.append(child)
                else:
                    self.read(child)

    def recheck(self):
        for rel in sorted(self.missing):
            if self.path(rel).exists():
                raise GreaError('STALE_INPUT', 'Previously absent input appeared during inspection.', details={'path': rel})
        for rel, token in self.tokens.items():
            self.check_cancel()
            if os.name=='nt':
                from .host.windows_files import path_token
                current=path_token(self.path(rel))
            else:current=self.token(self.path(rel).lstat())
            if current != token:
                raise GreaError('STALE_INPUT', 'Input changed before report completion.', details={'path': rel})
        for rel, names in list(self.directories.items()):
            if self.children(rel) != names:
                raise GreaError('STALE_INPUT', 'Directory membership changed during inspection.', details={'path': rel})


def _inspect(project_root, profile, mode, scope, baseline, max_files, max_bytes, cancel):
    reader = Reader(project_root, max_files, max_bytes, cancel)
    profile = relative(profile)
    p = strict_json(reader.read(profile, json_file=True), profile)
    errors = list(Draft202012Validator(PROFILE).iter_errors(p))
    if errors:
        first = sorted(errors, key=lambda e: str(list(e.path)))[0]
        raise GreaError('INVALID_PROFILE', 'Profile does not match unity-project schema v1.',
                        details={'path': list(first.path), 'validator': first.validator})
    if any(x in KEYWORDS for x in p['namespace'].split('.')) or any(x['name'] in KEYWORDS for x in p['modules']):
        raise GreaError('INVALID_PROFILE', 'C# namespace and module identifiers cannot be reserved keywords.')
    paths = p['paths']
    unity = relative(paths['unityProject'], allow_dot=True)
    def at(value):
        return str(PurePosixPath(unity) / value)
    managed = [at(x) for x in ('Assets', 'Packages', 'ProjectSettings')]
    for key in ('evidenceRoot', 'buildRoot'):
        relative(paths[key])
        if any(overlaps(paths[key], x) for x in managed) or overlaps(paths[key], profile):
            raise GreaError('INVALID_PROFILE', 'Evidence/build paths must not overlap managed inputs or profile.')
        reader.path(paths[key])
    if overlaps(paths['evidenceRoot'], paths['buildRoot']):
        raise GreaError('INVALID_PROFILE', 'Evidence and build roots must be separate.')
    if any(overlaps(profile, x) for x in managed):
        raise GreaError('INVALID_PROFILE', 'Profile must be outside Unity managed input trees.')
    for value in p['scenes'].values():
        relative(value)
        if not value.startswith('Assets/') or not value.endswith('.unity'):
            raise GreaError('INVALID_PROFILE', 'Scenes must use explicit Assets-relative .unity paths.')
        reader.path(at(value))
    if p['scenes']['bootstrap'] == p['scenes']['entry']:
        raise GreaError('INVALID_PROFILE', 'Bootstrap and content scene must be distinct in the reference profile.')
    if p['saveNamespace'] == p['qaSaveNamespace']:
        raise GreaError('INVALID_PROFILE', 'QA and player save namespaces must be distinct.')
    for module in p['modules']:
        relative(module['name'])
    module_names = [unicodedata.normalize('NFC', x['name']).casefold() for x in p['modules']]
    if len(set(module_names)) != len(module_names):
        raise GreaError('INVALID_PROFILE', 'Module names collide after portable normalization.')
    if 'lifecycle' not in p['features'] or ('ui' in p['features'] and 'resources' not in p['features']):
        raise GreaError('INVALID_PROFILE', 'Lifecycle is required; UI also requires resources.')
    for exception in p['exceptions']:
        relative(exception['scope']); reader.path(at(exception['scope']))
    if mode == 'refactor' and (not scope or not baseline):
        raise GreaError('BASELINE_REQUIRED', 'Refactor planning requires explicit Unity-relative scope and an existing evidence baseline file.')
    roots = scope or ['Assets', 'Packages', 'ProjectSettings']
    roots = sorted(set(relative(x) for x in roots))
    if any(PurePosixPath(x).parts[0] not in ('Assets', 'Packages', 'ProjectSettings') for x in roots):
        raise GreaError('INVALID_PROJECT_PATH', 'Scope is restricted to Assets, Packages and ProjectSettings.')
    if any(overlaps(a, b) for i, a in enumerate(roots) for b in roots[i+1:]):
        raise GreaError('INVALID_PROJECT_PATH', 'Scope entries must not overlap.')
    findings = []
    def finding(code, path, message, rule='STR-01', severity='error'):
        if len(findings) >= 10000:
            raise GreaError('RESOURCE_LIMIT', 'Finding budget exceeded; inspection is incomplete.')
        findings.append({'code': code, 'severity': severity, 'path': path, 'message': message[:1024], 'ruleId': rule})
    target = reader.path(unity)
    if target.exists() and not target.is_dir():
        raise GreaError('PATH_CONFLICT', 'Unity target is not a directory.')
    if mode == 'new':
        if target.exists() and reader.children(unity):
            finding('TARGET_NOT_EMPTY', unity, 'New mode requires an absent or empty Unity target; nothing will be overwritten.')
        if any(p['dependencyLock'].values()):
            finding('INVALID_NEW_LOCK', profile, 'New projects declare package versions but cannot claim existing lock fingerprints.', 'GEN-01')
    else:
        for name in ('Assets', 'Packages', 'ProjectSettings'):
            if not reader.path(at(name)).is_dir():
                finding('MISSING_PROJECT_DIRECTORY', at(name), 'An adopted project requires this Unity directory.')
    for rel in roots:
        reader.scan(at(rel))
        if rel.startswith('Assets/') and not rel.endswith('.meta') and reader.path(at(rel)+'.meta').is_file():
            reader.read(at(rel)+'.meta')
        if mode == 'refactor' and not reader.path(at(rel)).exists():
            finding('MISSING_SCOPE', at(rel), 'Requested refactor scope does not exist.')
    # Version and dependency locks always participate, even in a narrow refactor scope.
    specials = ['ProjectSettings/ProjectVersion.txt', 'Packages/manifest.json', 'Packages/packages-lock.json']
    for rel in specials:
        path = at(rel)
        if reader.path(path).is_file():
            reader.read(path, json_file=rel.endswith('.json'))
        elif mode != 'new':
            finding('MISSING_DEPENDENCY', path, 'Required version/lock input is missing.', 'GEN-01')
    base_identity = None
    if baseline:
        relative(baseline)
        if not PurePosixPath(baseline).is_relative_to(PurePosixPath(paths['evidenceRoot'])):
            raise GreaError('INVALID_PROJECT_PATH', 'Baseline must be an explicit file within evidenceRoot.')
        reader.read(baseline)
        base_identity = reader.identities[baseline]
    generated = False
    if mode == 'adopt' and scope is None and reader.path(at('Tools/Generated/manifests/project.json')).is_file():
        from .unity_generation import plan_generation
        generated = plan_generation(project_root, profile, cancel=cancel)['action'] == 'verify'
    version_path = at(specials[0])
    if version_path in reader.data:
        match = re.search(rb'^m_EditorVersion: ([^\r\n]+)', reader.data[version_path], re.M)
        if not match or match[1].decode('utf-8') != p['toolchain']['editorVersion']:
            finding('EDITOR_VERSION_MISMATCH', version_path, 'Declared and recorded Editor versions differ.', 'GEN-01')
    manifest_path, lock_path = at(specials[1]), at(specials[2])
    for rel, field in [(manifest_path, 'manifestSha256'), (lock_path, 'packagesLockSha256')]:
        if rel in reader.data and reader.identities[rel]['sha256'] != p['dependencyLock'][field] and not (generated and p['dependencyLock'][field] is None):
            finding('DEPENDENCY_LOCK_MISMATCH', rel, 'Profile fingerprint does not match this dependency input.', 'GEN-01')
    if manifest_path in reader.data and lock_path in reader.data:
        manifest = strict_json(reader.data[manifest_path], manifest_path)
        lock = strict_json(reader.data[lock_path], lock_path)
        dependencies = manifest.get('dependencies') if isinstance(manifest, dict) else None
        locked = lock.get('dependencies') if isinstance(lock, dict) else None
        if not isinstance(dependencies, dict) or not isinstance(locked, dict):
            finding('INVALID_DEPENDENCIES', manifest_path, 'Manifest and lock must contain dependency objects.', 'GEN-01')
        else:
            for name, locked_item in locked.items():
                if not isinstance(locked_item, dict) or (locked_item.get('source') not in ('registry', 'builtin') and not (generated and name.startswith('com.grea.') and locked_item.get('source') == 'embedded')):
                    finding('UNSUPPORTED_DEPENDENCY_SOURCE', lock_path, 'Lock entry has no supported registry/builtin source: '+name, 'STR-04')
            for name, expected in p['toolchain']['packages'].items():
                item = locked.get(name)
                if dependencies.get(name) != expected or not isinstance(item, dict) or item.get('version') != expected:
                    finding('MISSING_OR_MISMATCHED_PACKAGE', manifest_path, 'Required package does not match profile: '+name, 'GEN-01')
            for name, version in dependencies.items():
                if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?', version):
                    finding('UNSUPPORTED_DEPENDENCY_SOURCE', manifest_path, 'Static inspection does not resolve local, Git or unpinned dependency: '+name, 'STR-04')
                elif not isinstance(locked.get(name), dict) or locked[name].get('version') != version:
                    finding('MISSING_LOCK_ENTRY', lock_path, 'Direct package is absent or mismatched in lock: '+name, 'GEN-01')
    template_ok = p['template'] in (REFERENCE['template'], LEGACY_TEMPLATE)
    if not template_ok:
        finding('UNKNOWN_TEMPLATE', profile, 'Only the registered recipe or legacy design profile is recognized.', 'GEN-01')
    known = template_ok and p['toolchain'] == REFERENCE['toolchain'] and p['assetBackend'] == REFERENCE['assetBackend']
    if not known:
        finding('UNSUPPORTED_COMBINATION', profile, 'This combination is not in the static reference matrix; it will not be substituted.', 'GEN-01')
    if p['frameworkPackages']:
        finding('FRAMEWORK_OVERRIDE_UNSUPPORTED', profile, 'Explicit framework overrides are not resolved by this static operation; bundled recipe packages are verified by ownership.', 'CMP-01')
    if mode != 'new':
        for value in p['scenes'].values():
            rel = at(value)
            if not reader.path(rel).is_file():
                finding('MISSING_SCENE', rel, 'Declared scene input is missing; no scene will be synthesized.', 'PFB-04')
            else:
                reader.read(rel)
    _inventory_findings(reader, finding, at('Assets'))
    _assembly_findings(reader, finding, p['namespace'])
    reader.recheck()
    findings = list({digest(f): f for f in findings}.values())
    inventory = sorted(reader.identities.values(), key=lambda x: x['path'])
    snapshot = digest({'inventory': inventory, 'directories': reader.directories, 'absent': sorted(reader.missing)})
    capability = {'id': REFERENCE['id'] if known else None, 'staticPlanning': 'supported' if known else 'unsupported',
                  'editor': 'not_run', 'playMode': 'not_run', 'player': 'not_run', 'generation': 'not_run'}
    report = {'schemaVersion': 1, 'standardVersion': STANDARD_VERSION, 'plannerVersion': PLANNER_VERSION,
              'mode': mode, 'profileSha256': reader.identities[profile]['sha256'], 'snapshotSha256': snapshot,
              'scope': roots, 'inventory': inventory, 'findings': findings,
              'checks': [{'id': 'A0', 'status': 'fail' if any(f['severity']=='error' for f in findings) else 'pass', 'reason': 'Declared inputs, paths and explicit assembly metadata only.'},
                         *[{'id': level, 'status': 'not_run', 'reason': 'Not implemented or executed in static inspection.'} for level in ('A1', 'A2', 'A3', 'A4', 'A5')]],
              'capability': capability, 'staticStatus': 'fail' if any(f['severity']=='error' for f in findings) else 'pass',
              'compliance': 'not_assessed', 'limitations': LIMITATIONS}
    Draft202012Validator(REPORT).validate(report)
    return p, report, reader, at, base_identity


def _inventory_findings(reader, finding, assets_root):
    portable, guids = {}, {}
    for rel, row in sorted(reader.identities.items()):
        normalized = unicodedata.normalize('NFC', rel).casefold()
        if normalized in portable and portable[normalized] != rel:
            finding('PATH_COLLISION', rel, 'Portable path collides with '+portable[normalized])
        portable[normalized] = rel
        if row['guid']:
            if row['guid'] in guids:
                finding('DUPLICATE_GUID', rel, 'GUID duplicates '+guids[row['guid']], 'PFB-04')
            guids[row['guid']] = rel
        if rel.endswith('.meta') and PurePosixPath(rel).is_relative_to(PurePosixPath(assets_root)):
            if not row['guid']:
                finding('INVALID_META_GUID', rel, 'Meta input has no canonical GUID.', 'STR-03')
            if not reader.path(rel[:-5]).exists():
                finding('ORPHAN_META', rel, 'Meta file has no adjacent asset.', 'STR-03')
        if PurePosixPath(rel).is_relative_to(PurePosixPath(assets_root)) and rel != assets_root and not rel.endswith('.meta'):
            meta = rel+'.meta'
            if meta not in reader.identities:
                finding('MISSING_META', rel, 'Inspected asset has no inspected adjacent meta file.', 'STR-03')


def _assembly_findings(reader, finding, namespace):
    assemblies, by_guid = {}, {}
    for rel in sorted(reader.data):
        if not rel.endswith('.asmdef'):
            continue
        data = strict_json(reader.read(rel, json_file=True), rel)
        if (not isinstance(data, dict) or not isinstance(data.get('name'), str) or not data['name'] or len(data['name']) > 256
                or not isinstance(data.get('references', []), list) or len(data.get('references', [])) > 1000 or not all(isinstance(x, str) and 0 < len(x) <= 256 for x in data.get('references', []))
                or not isinstance(data.get('includePlatforms', []), list) or not all(isinstance(x, str) for x in data.get('includePlatforms', []))):
            finding('INVALID_ASSEMBLY_DEFINITION', rel, 'Assembly name, references or platforms have an invalid shape.', 'ARC-02')
            continue
        name = data['name']
        if name in assemblies:
            finding('DUPLICATE_ASSEMBLY', rel, 'Assembly name is not unique: '+name, 'ARC-01')
        assemblies[name] = (rel, data)
        guid = reader.identities.get(rel+'.meta', {}).get('guid')
        if guid:
            by_guid[guid] = name
        if (name == 'Grea.Foundation.Contracts' or any(name == namespace+'.'+role or name.startswith(namespace+'.'+role+'.') for role in ('Domain','Gameplay'))) and data.get('noEngineReferences') is not True:
            finding('ENGINE_DEPENDENT_RULES', rel, 'Pure rule/contract assemblies must declare noEngineReferences.', 'ARC-02')
        if 'Editor' in PurePosixPath(rel).parts and data.get('includePlatforms') != ['Editor']:
            finding('EDITOR_ASSEMBLY_NOT_ISOLATED', rel, 'Editor assembly must be restricted to Editor.', 'ARC-02')
    graph = {name: set() for name in assemblies}
    for name, (rel, data) in assemblies.items():
        for ref in data.get('references', []):
            target = by_guid.get(ref[5:]) if ref.startswith('GUID:') else ref
            if target not in assemblies:
                finding('UNRESOLVED_ASSEMBLY_REFERENCE', rel, 'Reference needs package/Editor resolution: '+ref, 'ARC-02', 'warning')
                continue
            graph[name].add(target)
            target_path, target_data = assemblies[target]
            source_editor = data.get('includePlatforms') == ['Editor']
            source_test = 'Tests' in PurePosixPath(rel).parts
            if not source_editor and not source_test and (target_data.get('includePlatforms') == ['Editor'] or 'Tests' in PurePosixPath(target_path).parts):
                finding('RUNTIME_EDITOR_TEST_REFERENCE', rel, 'Runtime references Editor/test assembly: '+target, 'ARC-02')
            if name.startswith('Grea.') and target.startswith(namespace+'.'):
                finding('FRAMEWORK_PROJECT_REFERENCE', rel, 'Shared framework cannot depend on project assemblies.', 'ARC-01')
            role = name.removeprefix(namespace+'.').split('.')[0]
            target_role = target.removeprefix(namespace+'.').split('.')[0]
            allowed = {'Domain': set(), 'Gameplay': {'Domain'}, 'Presentation': {'Gameplay', 'Domain'},
                       'Services': {'Gameplay', 'Domain'}, 'Diagnostics': {'Gameplay', 'Domain'}}
            if name.startswith(namespace+'.') and target.startswith(namespace+'.') and role in allowed and target_role not in allowed[role]:
                finding('ASSEMBLY_LAYER_VIOLATION', rel, 'Layer dependency is not allowed: '+target, 'ARC-01')
    indegree = {n: 0 for n in graph}
    for deps in graph.values():
        for dep in deps:
            indegree[dep] += 1
    queue = deque(n for n, degree in indegree.items() if degree == 0)
    while queue:
        for dep in graph[queue.popleft()]:
            indegree[dep] -= 1
            if indegree[dep] == 0:
                queue.append(dep)
    if any(indegree.values()):
        finding('ASSEMBLY_CYCLE', '', 'Explicit inspected assembly references contain a cycle.', 'ARC-01')


def validate_project(project_root, profile='grea-project.json', mode='adopt', scope=None, baseline=None,
                     max_files=2000, max_bytes=67108864, cancel=None):
    return _inspect(project_root, profile, mode, scope, baseline, max_files, max_bytes, cancel)[1]


def plan_project(project_root, profile='grea-project.json', mode='adopt', scope=None, baseline=None,
                 expected_plan_id=None, max_files=2000, max_bytes=67108864, cancel=None):
    p, report, reader, at, base = _inspect(project_root, profile, mode, scope, baseline, max_files, max_bytes, cancel)
    items = []
    def item(target, logical, owner, bindings=()):
        path = reader.path(target)
        before = reader.identities.get(target)
        if path.exists() and before is None:
            # Target-specific reads outside selected refactor scope are never implicit.
            return
        if mode == 'new' and not path.exists():
            action = 'create'
        else:
            action = 'preserve' if mode == 'adopt' else 'review'
        items.append({'action': action, 'logicalId': logical, 'target': target,
                      'expectedBeforeHash': before['sha256'] if before else None, 'owner': owner,
                      'preserveGuid': True, 'requiredBindings': list(bindings),
                      'reason': 'Design intent only; this operation does not write, move, delete or overwrite this target.',
                      'validationIds': ['GEN-02', 'GEN-03', 'PFB-04']})
    if mode == 'new' and report['staticStatus'] == 'pass' and p['template'] == REFERENCE['template']:
        from .unity_generation import _profile, _recipe
        recipe = _recipe(_profile(reader, profile))
        for name in sorted(recipe):
            item(at(name), 'recipe:'+name, 'package' if name.startswith('Packages/') else 'seed-once')
        for name, path in p['scenes'].items():
            item(at(path), 'scene:'+name, 'generated', ['Editor-generated bindings'])
    elif mode == 'new' and report['staticStatus'] == 'pass':
        item(at('ProjectSettings/ProjectVersion.txt'), 'project:editor', 'generated')
        item(at('Packages/manifest.json'), 'project:packages', 'generated')
        item(at('Assets/Game/Runtime/Bootstrap/Bootstrap.cs'), 'project:bootstrap', 'seed-once')
        for module in p['modules']:
            for layer in sorted(module['layers']):
                item(at(f'Assets/Game/Runtime/{layer}/{module["name"]}/{module["name"]}.cs'), 'module:'+module['name']+':'+layer, 'seed-once')
        for name, path in p['scenes'].items():
            item(at(path), 'scene:'+name, 'generated', ['Bootstrap scope'] if name == 'bootstrap' else ['Content entry'])
    else:
        for row in report['inventory']:
            if any(PurePosixPath(row['path']).is_relative_to(PurePosixPath(at(s))) for s in report['scope']):
                item(row['path'], 'existing:'+hashlib.sha256(row['path'].encode()).hexdigest(), 'human')
    reader.recheck()
    inputs = {'profile': report['profileSha256'], 'snapshot': report['snapshotSha256'], 'scope': report['scope'],
              'mode': mode, 'baseline': base, 'reference': REFERENCE, 'planner': PLANNER_VERSION,
              'implementation': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'contracts': digest(documents())}
    result = {'schemaVersion': 1, 'standardVersion': STANDARD_VERSION, 'plannerVersion': PLANNER_VERSION,
              'mode': mode, 'projectId': p['projectId'], 'profileSha256': report['profileSha256'],
              'snapshotSha256': report['snapshotSha256'], 'inputsSha256': digest(inputs),
              'template': p['template'], 'scope': report['scope'], 'baseline': base, 'items': items,
              'blockers': sorted(set(['USE_GENERATION_PLAN'] + [f['code'] for f in report['findings']])),
              'generationReady': False, 'report': report}
    result['planId'] = digest(result)
    if expected_plan_id is not None and expected_plan_id != result['planId']:
        raise GreaError('STALE_PLAN', 'Current inputs no longer match the supplied plan identity.', details={'current_plan_id': result['planId']})
    Draft202012Validator(PLAN).validate(result)
    return result
