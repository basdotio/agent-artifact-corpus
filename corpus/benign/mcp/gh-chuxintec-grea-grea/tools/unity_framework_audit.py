"""Read-only source/asmdef boundary guard for the shipped packages and one consumer.

This is a bounded source guard, not a C# compiler, reflection or Player payload audit.
"""
import json
from grea.host.paths import Path
import re


def inspect(packages, sample=None):
    roots = [('packages', Path(packages))]
    if sample is not None:
        roots.append(('sample', Path(sample)))
    nodes, folders, findings = {}, [], []

    def report(code, path, **details):
        findings.append(dict(code=code, path=path, **details))

    for label, root in roots:
        if not root.is_dir():
            report('MISSING_SOURCE_ROOT', label)
            continue
        if root.is_symlink():
            report('SOURCE_LINK', label)
            continue
        for path in sorted(root.rglob('*.asmdef')):
            relative = label + '/' + path.relative_to(root).as_posix()
            if path.is_symlink():
                report('SOURCE_LINK', relative)
                continue
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
                name, refs = data['name'], data.get('references', [])
                if not isinstance(name, str) or not isinstance(refs, list) or not all(isinstance(r, str) for r in refs):
                    raise ValueError('Invalid assembly name/references')
            except (ValueError, KeyError, TypeError):
                report('INVALID_ASSEMBLY', relative)
                continue
            if name in nodes:
                report('DUPLICATE_ASSEMBLY', relative, assembly=name)
                continue
            node = dict(data=data, path=relative, package=label == 'packages')
            nodes[name] = node
            folders.append((path.parent, name))
            pure = name == 'Grea.Foundation.Contracts' or name.endswith(('.Domain', '.Gameplay'))
            test = 'TestAssemblies' in data.get('optionalUnityReferences', []) or 'Tests' in name.split('.')
            if pure and not data.get('noEngineReferences'):
                report('PURE_LAYER_ENGINE_ENABLED', relative, assembly=name)
            if test and 'UNITY_INCLUDE_TESTS' not in data.get('defineConstraints', []):
                report('TEST_PLAYER_LEAK', relative, assembly=name)
            node['pure'], node['test'] = pure or bool(data.get('noEngineReferences')), test
        if not any(node['path'].startswith(label + '/') for node in nodes.values()):
            report('INSUFFICIENT_COVERAGE', label, reason='No assemblies were found in this selected root')

    for name, node in nodes.items():
        for ref in node['data'].get('references', []):
            if ref.startswith('GUID:'):
                report('UNSUPPORTED_GUID_REFERENCE', node['path'], reference=ref)
            target = nodes.get(ref)
            if node['package'] and (target and not target['package'] or re.match(r'^(Game|IceFire)(\.|$)', ref)):
                report('PACKAGE_PROJECT_REFERENCE', node['path'], reference=ref)
            if node['pure'] and (ref.startswith(('UnityEngine', 'UnityEditor', 'Unity.')) or target and not target['pure']):
                report('PURE_LAYER_ENGINE_REFERENCE', node['path'], reference=ref)
            if not node['test'] and 'Editor' not in node['data'].get('includePlatforms', []):
                if ref.startswith('UnityEditor') or 'Editor' in ref.split('.') or target and target['test']:
                    report('RUNTIME_EDITOR_OR_TEST_REFERENCE', node['path'], reference=ref)

    states = {}

    def visit(name, chain):
        if states.get(name) == 'visiting':
            report('ASSEMBLY_CYCLE', nodes[name]['path'], cycle=chain[chain.index(name):] + [name])
            return
        if name in states:
            return
        states[name] = 'visiting'
        for ref in nodes[name]['data'].get('references', []):
            if ref in nodes:
                visit(ref, chain + [name])
        states[name] = 'done'

    for name in nodes:
        visit(name, [])

    # Associate a script with its nearest asmdef; nested assemblies remain separate.
    folders.sort(key=lambda item: -len(item[0].parts))
    lexical = re.compile(r'@"(?:""|[^"])*"|"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/', re.S)
    for label, root in roots:
        if root.is_symlink():
            continue
        for path in sorted(root.rglob('*.cs')):
            relative = label + '/' + path.relative_to(root).as_posix()
            if path.is_symlink():
                report('SOURCE_LINK', relative)
                continue
            owner = next((nodes[name] for folder, name in folders if folder in path.parents), None)
            if owner is None:
                report('SCRIPT_WITHOUT_ASSEMBLY', relative)
                continue
            text = lexical.sub('', path.read_text(encoding='utf-8'))
            if owner['pure'] and re.search(r'\b(?:UnityEngine|UnityEditor)\b', text):
                report('PURE_LAYER_ENGINE_SOURCE', relative)
            if owner['package'] and re.search(r'\b(?:using|namespace)\s+(?:Game|IceFire)(?:\.|\s|;)', text):
                report('PACKAGE_PROJECT_SOURCE', relative)
            if not owner['test'] and re.search(r'\bNUnit\b', text):
                report('TEST_PLAYER_SOURCE', relative)
    return dict(ok=not findings, assemblies=len(nodes), findings=findings,
                scope='Selected source and named asmdef references; Unity compilation and Player audit remain required.')
