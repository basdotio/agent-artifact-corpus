"""Canonical CLI/MCP contracts. Catalogs and advertised schemas derive from here."""
from . import __version__

MODES = ('recover', 'fix', 'reskin', 'refactor', 'performance', 'deliver', 'maintain')
DIMENSIONS = ('rules', 'runtime', 'visual', 'identity', 'performance', 'platform')
KINDS = ('original_static', 'original_runtime', 'candidate_runtime', 'approved_design', 'test_report', 'build_manifest')

def obj(properties=None, required=()):
    return {'type': 'object', 'properties': properties or {}, 'required': list(required), 'additionalProperties': False}

def string(description='', enum=None):
    out = {'type': 'string', 'minLength': 1, 'description': description}
    if enum is not None: out['enum'] = list(enum)
    return out

def integer(default, minimum=1, maximum=None):
    out = {'type': 'integer', 'minimum': minimum, 'default': default}
    if maximum is not None: out['maximum'] = maximum
    return out

def array(items): return {'type': 'array', 'items': items}
PATH = string('Explicit local path; do not substitute a historical path.')
TOOL = string('Exact tool ID from list_tools; no implicit provider substitution.')
CASE = string('Project .grea case directory, or its owning project directory.')

CONTRACTS = {
 'session': ('Inspect grea identity, catalog digest and readiness without launching providers; optionally check an installed Skill.', obj({'skill_dir': PATH}), []),
 'list_tools': ('List the complete registered provider/helper inventory, including unavailable entries.', obj({'category': string()}), []),
 'describe_tool': ('Read one registered tool contract, effects, command and limitations.', obj({'tool_id': TOOL}, ['tool_id']), []),
 'doctor': ('Inspect installation presence; only run explicit selected version/help probes when probe=true.', obj({'tool_ids': array(TOOL), 'probe': {'type':'boolean','default':False}}), ['process_when_probe_requested']),
 'inspect_target': ('Inventory a supplied artifact with content digests and explicit partial coverage; never execute it.', obj({'path': PATH, 'max_files': integer(1000,1,100000), 'max_bytes': integer(268435456,1,17179869184)}, ['path']), ['filesystem_read']),
 'plan_workflow': ('Select scoped Unity recovery steps, evidence dimensions, tools and canonical references; does not execute the plan.', obj({'mode': string(enum=MODES), 'source_engine': string(enum=('unity','laya','other'))}, ['mode']), []),
 'run_tool': ('Run one exact registered command with explicit argv and a new log directory; preserve nonzero/timeout/partial outcomes. Does not grant approval or assert game parity.', obj({'tool_id': TOOL, 'arguments': array({'type':'string'}), 'working_directory': string('Optional existing absolute cwd; default is the new run directory. argv is never guessed or rewritten.'), 'run_dir': PATH, 'timeout_seconds': integer(120,1,3600), 'max_output_bytes': integer(16777216,1024,1073741824), 'max_inline_bytes': integer(32768,256,1048576)}, ['tool_id','arguments','run_dir']), ['process','filesystem_write','provider_declared_effects']),
 'init_case': ('Create a project-local immutable baseline and explicit required acceptance dimensions. Existing cases are not overwritten.', obj({'project_dir': PATH, 'source': PATH, 'mode': string(enum=MODES), 'required_dimensions': array(string(enum=DIMENSIONS))}, ['project_dir','source','mode']), ['filesystem_write']),
 'add_evidence': ('Register an existing evidence file and its source/candidate role with a verified digest. The role is caller-declared, not authenticated original gameplay.', obj({'case_dir': CASE,'kind':string(enum=KINDS),'path':PATH,'description':string()}, ['case_dir','kind','path','description']), ['filesystem_read','filesystem_write']),
 'record_verification': ('Record an explicit reviewer verdict for one dimension, bound to existing evidence IDs. It records a claim; it does not run tests or inspect images.', obj({'case_dir':CASE,'dimension':string(enum=DIMENSIONS),'status':string(enum=('passed','failed','not_run','not_applicable')),'evidence_ids':array(string()),'note':string()}, ['case_dir','dimension','status','evidence_ids','note']), ['filesystem_write']),
 'case_status': ('Recheck source/evidence integrity and report declared verdicts, missing coverage and contradictions. Static evidence cannot substitute for runtime/visual proof.', obj({'case_dir':CASE}, ['case_dir']), ['filesystem_read']),
}

# Typed Unity outcomes reuse existing adapters; generic argv remains only the compatibility/advanced surface.
_RUN = {k: v for k, v in CONTRACTS['run_tool'][1]['properties'].items() if k in ('run_dir','timeout_seconds','max_output_bytes','max_inline_bytes')}
CONTRACTS.update({
 'audit_unity_dependencies': ('Audit a Unity Assets text-GUID dependency closure from explicit root assets. Dynamic references still require Editor verification.', obj(dict(_RUN, assets=PATH, roots=dict(array(string()),minItems=1), output=PATH), ['assets','roots','output','run_dir']), ['filesystem_read','filesystem_write','process']),
 'snapshot_unity_assets': ('Snapshot Unity asset paths, GUIDs, contents and Resources keys without moving assets or modifying Unity.', obj(dict(_RUN, assets=PATH, output=PATH), ['assets','output','run_dir']), ['filesystem_read','filesystem_write','process']),
 'compare_gameplay_traces': ('Find the first divergence between two ordered gameplay JSONL traces at explicit JSON Pointer fields. Does not establish correct sampling or reorder concurrent events.', obj(dict(_RUN, before=PATH, after=PATH, fields=dict(array({'type':'string'}),minItems=1)), ['before','after','fields','run_dir']), ['filesystem_read','filesystem_write','process']),
 'inspect_numeric_texture': ('Validate raw floating-point texture bytes (VAT/numeric maps); ordinary PNG imagery is not equivalent numeric evidence.', obj(dict(_RUN, source=PATH, width=integer(1), height=integer(1), channels=integer(4,1,4), dtype=string(enum=('f16','f32')), endian=dict(string(enum=('little','big')),default='little'), candidate=PATH), ['source','width','height','channels','dtype','run_dir']), ['filesystem_read','filesystem_write','process']),
})

# Static inspection and generation have separate operation and plan contracts.
from .unity_project_contracts import documents as unity_documents, capability_matrix
_UNITY_INPUT = {'project_root': PATH, 'profile': dict(PATH, default='grea-project.json', description='Project-root-relative profile JSON path; absolute paths are rejected.'),
                'mode': dict(string(enum=('new','adopt','refactor')), default='adopt'),
                'scope': dict(array(string()), minItems=1, maxItems=100, uniqueItems=True),
                'baseline': string('Project-root-relative existing file within evidenceRoot; caller-declared behavioral baseline.'), 'max_files': integer(2000,1,100000),
                'max_bytes': integer(67108864,1,1073741824)}
CONTRACTS.update({
 'validate_unity_project': ('Read-only profile/path/dependency/assembly checks. No Unity launch, writes or runtime acceptance.', obj(_UNITY_INPUT, ['project_root']), ['filesystem_read']),
 'plan_unity_project': ('Create a deterministic design-only Unity plan on stdout. No generation or project writes; generationReady is always false for this read-only operation.', obj(dict(_UNITY_INPUT, expected_plan_id={'type':'string','pattern':'^[0-9a-f]{64}$'}), ['project_root']), ['filesystem_read']),
})

_GEN = {'project_root': PATH, 'profile': dict(PATH, default='grea-project.json')}
_GEN_RUN = dict(_GEN, run_dir=string('Project-root-relative new evidence directory, or exact previous run for recovery.'),
                timeout_seconds=integer(240, 1, 3600), max_output_bytes=integer(16777216, 1024, 1073741824),
                max_inline_bytes=integer(32768, 256, 1048576))
CONTRACTS.update({
 'plan_unity_generation': ('Plan create-only recipe or read-only adopt. No Unity process or writes.', obj(dict(_GEN, mode=dict(string(enum=('new','adopt')), default='new')), ['project_root']), ['filesystem_read']),
 'generate_unity_project': ('Generate a new staged Unity project with Editor-created prefabs, verify and publish. Existing owned projects are verified without overwrites.', obj(dict(_GEN_RUN, plan_id={'type':'string','pattern':'^[0-9a-f]{64}$'}), ['project_root','run_dir','plan_id']), ['filesystem_read','filesystem_write','process']),
 'recover_unity_generation': ('Resume a specific interrupted generation run after identity checks. Conflicts are retained; no automatic deletion or overwrite.', obj(_GEN_RUN, ['project_root','run_dir']), ['filesystem_read','filesystem_write','process']),
})

ERROR_SCHEMA = obj({'code': string(), 'message':string(), 'retryable':{'type':'boolean'}, 'details':{'type':'object'}, 'next_action':string()}, ['code','message','retryable','details','next_action'])
ENVELOPE_SCHEMA = obj({
 'schema_version':{'const':1}, 'product':{'const':'grea'}, 'version':string(), 'operation':string(), 'run_id':string(),
 'status':{'enum':['ok','partial','error']}, 'result':{'type':['object','null']},
 'evidence':array({'type':'object'}), 'limitations':array({'type':'string'}), 'limits':{'type':'object'},
 'error':{'anyOf':[ERROR_SCHEMA,{'type':'null'}]},
}, ['schema_version','product','version','operation','run_id','status','result','evidence','limitations','limits','error'])

def catalog():
    return [{'name': name, 'description': description, 'inputSchema': schema,
             'outputSchema': ENVELOPE_SCHEMA, 'effects': effects,
             'annotations': {'readOnlyHint': not any(x in effects for x in ('filesystem_write','process','process_when_probe_requested')), 'destructiveHint': name=='run_tool', 'idempotentHint': name in ('session','list_tools','describe_tool','plan_workflow','inspect_target','case_status','validate_unity_project','plan_unity_project','plan_unity_generation'), 'openWorldHint':name in ('run_tool','generate_unity_project','recover_unity_generation')}}
            for name,(description,schema,effects) in CONTRACTS.items()]
