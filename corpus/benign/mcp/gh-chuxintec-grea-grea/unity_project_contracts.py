"""Versioned Unity project document contracts; exported by generate_contracts.py.

Static plans and executable generation plans are distinct contracts.
"""
from copy import deepcopy

DRAFT = 'https://json-schema.org/draft/2020-12/schema'
STANDARD_VERSION = '1.0.0'
PLANNER_VERSION = '1.0.0'
TEMPLATE_ID = 'grea-minimal-2d'
TEMPLATE_VERSION = '0.1.0'
LEGACY_TEMPLATE = {'id': TEMPLATE_ID, 'version': '0.1.0-design'}
LAYERS = ('Domain', 'Gameplay', 'Presentation', 'Services', 'Diagnostics')
FEATURES = ('lifecycle', 'ui', 'resources', 'audio', 'save', 'diagnostics')


def obj(props, required=None):
    return {'type': 'object', 'properties': props, 'required': list(props if required is None else required), 'additionalProperties': False}


def text(pattern=None):
    value = {'type': 'string', 'minLength': 1, 'maxLength': 1024}
    if pattern:
        value['pattern'] = pattern
    return value


def enum(*values):
    return {'type': 'string', 'enum': list(values)}


def array(item, minimum=0, maximum=1000):
    return {'type': 'array', 'items': item, 'minItems': minimum, 'maxItems': maximum, 'uniqueItems': True}


HASH = text(r'^[0-9a-f]{64}$')
NULL_HASH = {'anyOf': [HASH, {'type': 'null'}]}
VERSION = text(r'^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$')
IDENTIFIER = text(r'^[A-Za-z_][A-Za-z0-9_]*$')
PATH = text()  # Portability and containment are checked semantically, on every component.
SCHEMA_VERSION = {'type': 'integer', 'const': 1}
TOOLCHAIN = obj({
    'editorVersion': text(r'^\d{4}\.\d+\.\d+[abfp]\d+$'),
    'renderPipeline': enum('urp', 'hdrp', 'builtin'), 'ui': enum('ugui', 'uitk'),
    'input': enum('legacy', 'input-system'),
    'targetPlatform': enum('macOS', 'Windows', 'Linux', 'Android', 'iOS', 'WebGL'),
    'architecture': enum('arm64', 'x86_64', 'universal', 'wasm'),
    'scriptingBackend': enum('Mono', 'IL2CPP'),
    'packages': {'type': 'object', 'patternProperties': {r'^[a-z][a-z0-9.-]+$': VERSION}, 'additionalProperties': False, 'maxProperties': 100},
})
PROFILE = obj({
    'schemaVersion': SCHEMA_VERSION, 'standardVersion': {'const': STANDARD_VERSION},
    'projectId': text(r'^[a-z][a-z0-9-]{0,63}$'),
    'namespace': text(r'^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$'),
    'paths': obj({'unityProject': PATH, 'evidenceRoot': PATH, 'buildRoot': PATH}),
    'toolchain': TOOLCHAIN,
    'dependencyLock': obj({'manifestSha256': NULL_HASH, 'packagesLockSha256': NULL_HASH}),
    'template': obj({'id': text(), 'version': VERSION}),
    'frameworkPackages': array(obj({'name': text(r'^com\.grea\.[a-z0-9.-]+$'), 'version': VERSION, 'sha256': HASH}), maximum=20),
    'features': array(enum(*FEATURES), 1, 20),
    'modules': array(obj({'name': IDENTIFIER, 'layers': array(enum(*LAYERS), 1, len(LAYERS))}), 1, 100),
    'scenes': obj({'bootstrap': PATH, 'entry': PATH}),
    'assetBackend': enum('catalog', 'resources', 'addressables', 'assetbundle'),
    'saveNamespace': text(r'^[a-zA-Z0-9_.-]+$'), 'qaSaveNamespace': text(r'^[a-zA-Z0-9_.-]+$'),
    'exceptions': array(obj({'ruleId': text(r'^(STR|ARC|LIF|DAT|CMP|PFB|SCR|GEN|ACC|UPG)-\d{2}$'), 'scope': PATH,
                             'reason': text(), 'alternative': text(), 'verification': text(), 'owner': text(), 'reviewTrigger': text()}), maximum=100),
})
FILE_IDENTITY = obj({'path': PATH, 'kind': enum('file', 'directory'), 'bytes': {'type': 'integer', 'minimum': 0},
                     'sha256': NULL_HASH, 'guid': {'anyOf': [text(r'^[0-9a-f]{32}$'), {'type': 'null'}]}})
FINDING = obj({'code': text(), 'severity': enum('error', 'warning'), 'path': {'type': 'string'}, 'message': text(), 'ruleId': text()})
CHECK = obj({'id': text(), 'status': enum('pass', 'fail', 'not_run', 'not_applicable'), 'reason': text()})
CAPABILITY = obj({'id': {'type': ['string', 'null']}, 'staticPlanning': enum('supported', 'unsupported'),
                  'editor': {'const': 'not_run'}, 'playMode': {'const': 'not_run'}, 'player': {'const': 'not_run'},
                  'generation': {'const': 'not_run'}})
REPORT = obj({'schemaVersion': SCHEMA_VERSION, 'standardVersion': {'const': STANDARD_VERSION},
              'plannerVersion': {'const': PLANNER_VERSION}, 'mode': enum('new', 'adopt', 'refactor'),
              'profileSha256': HASH, 'snapshotSha256': HASH, 'scope': array(PATH, 1),
              'inventory': array(FILE_IDENTITY, maximum=100000), 'findings': array(FINDING, maximum=10000),
              'checks': array(CHECK), 'capability': CAPABILITY, 'staticStatus': enum('pass', 'fail'),
              'compliance': {'const': 'not_assessed'}, 'limitations': array(text())})
PLAN_ITEM = obj({'action': enum('create', 'review', 'preserve'), 'logicalId': text(), 'target': PATH,
                 'expectedBeforeHash': NULL_HASH, 'owner': enum('seed-once', 'generated', 'human', 'package'),
                 'preserveGuid': {'type': 'boolean'}, 'requiredBindings': array(text()), 'reason': text(), 'validationIds': array(text(), 1)})
PLAN = obj({'schemaVersion': SCHEMA_VERSION, 'standardVersion': {'const': STANDARD_VERSION},
            'plannerVersion': {'const': PLANNER_VERSION}, 'planId': HASH,
            'mode': enum('new', 'adopt', 'refactor'), 'projectId': text(), 'profileSha256': HASH,
            'snapshotSha256': HASH, 'inputsSha256': HASH, 'template': deepcopy(PROFILE['properties']['template']),
            'scope': array(PATH, 1), 'baseline': {'anyOf': [FILE_IDENTITY, {'type': 'null'}]},
            'items': array(PLAN_ITEM, maximum=100000), 'blockers': array(text()), 'generationReady': {'const': False},
            'report': REPORT})
MANIFEST = obj({'schemaVersion': SCHEMA_VERSION, 'standardVersion': {'const': STANDARD_VERSION},
                'projectId': text(), 'planId': HASH, 'generatorVersion': VERSION,
                'template': deepcopy(PROFILE['properties']['template']), 'previousManifestSha256': NULL_HASH,
                'files': array(obj({'logicalId': text(), 'path': PATH, 'sha256': HASH,
                                    'metaSha256': NULL_HASH, 'guid': {'anyOf': [text(r'^[0-9a-f]{32}$'), {'type': 'null'}]},
                                    'fileIds': array(text(r'^-?\d+$')), 'owner': enum('seed-once', 'generated', 'human', 'package')}), maximum=100000)})
# Optional in the original document contract; mandatory for the M3 create-only executor.
MANIFEST['properties']['recipeId'] = HASH

GENERATION_PLAN = obj({
    'schemaVersion': SCHEMA_VERSION, 'generatorVersion': VERSION, 'template': deepcopy(PROFILE['properties']['template']),
    'recipeId': HASH, 'planId': HASH, 'projectId': text(), 'target': PATH, 'mode': enum('new','adopt'),
    'action': enum('create','verify','preserve'), 'profileSha256': HASH, 'snapshotSha256': HASH,
    'sourceFiles': {'type':'object','additionalProperties':HASH}, 'seedChanges': array(PATH), 'humanFiles': array(PATH),
    'generationReady': {'type':'boolean'}, 'limitations': array(text()), 'requiredEditorAssets': array(PATH),
    'items': array(PLAN_ITEM, maximum=100000),
    'ownership': {'type':'object','additionalProperties':enum('generated','package','seed-once','human')},
})


def documents():
    return {f'unity-{name}.schema.json': dict(deepcopy(value), **{'$schema': DRAFT})
            for name, value in [('project', PROFILE), ('plan', PLAN), ('manifest', MANIFEST), ('report', REPORT), ('generation-plan', GENERATION_PLAN)]}


REFERENCE = {
    'id': 'unity-6000.6.2f1-urp17.6-ugui2.6-macos-arm64-mono',
    'toolchain': {'editorVersion': '6000.6.2f1', 'renderPipeline': 'urp', 'ui': 'ugui', 'input': 'legacy',
                  'targetPlatform': 'macOS', 'architecture': 'arm64', 'scriptingBackend': 'Mono',
                  'packages': {'com.unity.render-pipelines.universal': '17.6.0', 'com.unity.ugui': '2.6.0'}},
    'assetBackend': 'catalog', 'template': {'id': TEMPLATE_ID, 'version': TEMPLATE_VERSION},
    'evidence': {'editorAndPackageMetadata': 'observed_on_2026-10-13', 'staticPlanning': 'synthetic_tests',
                 'editor': 'not_run', 'playMode': 'not_run', 'player': 'not_run', 'generation': 'not_run'},
}


def capability_matrix():
    return {'schemaVersion': 1, 'standardVersion': STANDARD_VERSION, 'plannerVersion': PLANNER_VERSION,
            'scope': 'Combination observations describe static planning only; executable create-only generation is exposed separately. Named reference game evidence is scoped separately and never applied to arbitrary projects.',
            'combinations': [deepcopy(REFERENCE)],
            'profileRecipes': [{'id':'modern-ui-v1','version':'0.1.0','status':'candidate','renderPipeline':'builtin','ui':'ugui-tmp','input':'input-system','editor':'6000.6.2f1','definition':'tools/unity/profiles/modern-ui/profile.json','validation':'validation/releases/2026-10-16-audit-remediation.json','scope':'Opt-in sample preparation only; not a supported plan_unity_project generation override.'}],
            'referenceGames': [{
                'id': 'signal-garden', 'version': '1.0.0',
                'editor': '6000.6.2f1', 'urp': '17.6.0', 'ugui': '2.6.0',
                'testFramework': '1.8.0', 'frameworkPackages': '0.2.0',
                'template': {'id': 'grea-minimal-2d', 'version': '0.1.0'},
                'target': 'macOS', 'architecture': 'arm64', 'backend': 'Mono',
                'managedStripping': 'Medium', 'input': 'legacy',
                'evidence': 'validation/releases/2026-10-13-unity-m4.json',
                'gates': {'A0': 'pass', 'A1': 'pass', 'A2': 'pass', 'A3': 'pass', 'A4': 'pass', 'A5': 'not_run'},
                'scope': 'Self-authored reference only; human Player input and scoped output evidence. No original-game parity, offline restore or other platform/backend claim.'
            }, {
                'id': 'signal-garden', 'version': '1.0.1',
                'editor': '6000.6.2f1', 'urp': '17.6.0', 'ugui': '2.6.0',
                'testFramework': '1.8.0', 'frameworkPackages': '0.2.1',
                'template': {'id': 'grea-minimal-2d', 'version': '0.1.0'},
                'target': 'macOS', 'architecture': 'arm64', 'backend': 'Mono',
                'managedStripping': 'Medium', 'input': 'legacy',
                'evidence': 'validation/releases/2026-10-14-reference-player-1.0.1.json',
                'gates': {'A0': 'pass', 'A1': 'pass', 'A2': 'pass', 'A3': 'pass', 'A4': 'pass', 'A5': 'not_run'},
                'scope': 'Isolated restored source and independently unpacked Player only; human input, reopen, focus-loss and mixer evidence. No other project/platform, offline or performance claim.'
            }]}
