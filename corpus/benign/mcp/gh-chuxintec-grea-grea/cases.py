"""Project-local immutable baseline, evidence records and explicit reviewer assertions."""
import json,uuid,time,contextlib,tempfile,shutil
from grea.host.paths import Path
from .common import GreaError,digest,write_new,now,publish_directory
from .case_hashing import hash_file, audit_hashes, audit_report
from .host.files import is_link
from .workflows import WORKFLOWS, required_dimensions as workflow_dimensions

def locate(path):
    path=Path(path).expanduser()
    if path.name!='.grea':path=path/'.grea'
    if is_link(path) or not (path/'case.json').is_file():raise GreaError('CASE_NOT_FOUND','No case at the requested project.',details={'path':str(path)})
    return path.resolve()

def load_case(root):
    value=json.loads((root/'case.json').read_text(encoding='utf-8'))
    claim=value.copy();fingerprint=claim.pop('case_id',None)
    if not fingerprint or fingerprint!='case_'+digest(claim):raise GreaError('TAMPERED_CASE','Case baseline digest does not match.')
    return value

@contextlib.contextmanager
def locked(root, write=True):
    from .host.files import file_lock
    lock=root/'.lock'
    if is_link(lock):raise GreaError('INVALID_CASE','Case lock may not be a symlink.')
    if not lock.is_file():raise GreaError('INVALID_CASE','Case lock file is missing.')
    with file_lock(lock, write=write):yield

def check_source(case):
    actual=hash_file(case['source']['path'])
    if actual['sha256']!=case['source']['sha256']:raise GreaError('STALE_SOURCE','The baseline source changed; create a new case.',details={'expected':case['source']['sha256'],'actual':actual['sha256']})

def init_case(project_dir,source,mode,required_dimensions=None,source_engine='unknown',engine_version=None,source_format=None,target_platform=None,acceptance_profile='scoped'):
    project=Path(project_dir).expanduser()
    if is_link(project) or not project.is_dir():raise GreaError('INVALID_PROJECT','Choose an existing real project directory.')
    from .case_revisions import identity as file_identity
    identity=file_identity(project.resolve(), source)
    mandatory=workflow_dimensions(mode, source_engine)
    dims=required_dimensions if required_dimensions is not None else mandatory
    if 'native' in mandatory and 'native' not in dims:raise GreaError('REQUIRED_DIMENSION','Cross-engine native acceptance cannot be removed.')
    if not dims or len(dims)!=len(set(dims)):raise GreaError('INVALID_REQUIREMENTS','Required dimensions must be nonempty and unique.')
    root=project.resolve()/'.grea'
    if root.exists() or root.is_symlink():raise GreaError('OUTPUT_EXISTS','Project already has a case; preserve it rather than overwrite.')
    value={'schema_version':2,'task':dict(intent=mode,source_engine=source_engine,engine_version=engine_version,source_format=source_format,target_platform=target_platform,acceptance_profile=acceptance_profile),'created_at':now(),'nonce':uuid.uuid4().hex,'project_dir':str(project.resolve()),'mode':mode,'source':identity,'required_dimensions':dims}
    value['case_id']='case_'+digest(value)
    from .host.files import private_directory
    stage=private_directory(project.resolve(),'.grea-init-')
    try:
        (stage/'.lock').touch(exist_ok=False)
        (stage/'evidence').mkdir();(stage/'verifications').mkdir();(stage/'revisions').mkdir()
        write_new(stage/'case.json',value)
        publish_directory(stage,root)
    finally:
        if stage.exists():shutil.rmtree(stage)
    return {'case_dir':str(root),'case':value,'acceptance':'not_run'}

def read_record(path,prefix):
    if is_link(path):raise GreaError('TAMPERED_EVIDENCE','Record is a symlink.')
    value=json.loads(path.read_text(encoding='utf-8'));body=value.copy();rid=body.pop('id',None)
    if rid!=prefix+digest(body):raise GreaError('TAMPERED_EVIDENCE','Record content does not match its ID.',details={'record':str(path)})
    return value

def next_order(root, directory, prefix):
    """Allocate strict append order while the caller holds the Case write lock."""
    previous = (read_record(path, prefix)['order_ns'] for path in (root/directory).glob('*.json'))
    return max(time.time_ns(), max(previous, default=-1) + 1)

def evidence_records(root,case):
    values={}
    if (root/'evidence').is_symlink():raise GreaError('TAMPERED_EVIDENCE','Evidence directory is a symlink.')
    for p in sorted((root/'evidence').glob('*.json')):
        value=read_record(p,'ev_')
        if value['case_id']!=case['case_id']:raise GreaError('WRONG_CASE','Evidence belongs to another baseline.')
        actual=hash_file(value['artifact']['path'])
        if actual['sha256']!=value['artifact']['sha256']:raise GreaError('STALE_EVIDENCE','Evidence artifact changed.',details={'evidence_id':value['id']})
        values[value['id']]=value
    return values

def modern(root):
    return load_case(root).get('schema_version',1)>=2 or any((root/'revisions').glob('*.json'))

def add_evidence(case_dir,kind,path,description,revision_id=None,run_instance=None):
    root=locate(case_dir)
    if modern(root):
        from .case_revisions import add
        return add(case_dir,kind,path,description,revision_id,run_instance)
    with locked(root):
        case=load_case(root);check_source(case)
        p=Path(path).expanduser().resolve()
        if root==p or root in p.parents:raise GreaError('INVALID_EVIDENCE','Evidence artifact must be outside the case metadata directory.')
        value={'case_id':case['case_id'],'kind':kind,'artifact':hash_file(path),'description':description,'authority':'caller_declared_role','created_at':now(),'nonce':uuid.uuid4().hex}
        value['id']='ev_'+digest(value);write_new(root/'evidence'/f"{value['id']}.json",value)
    return {'evidence':value,'limitations':['A file hash proves identity; role and meaning are reviewer assertions.']}

def required_kinds(mode,dimension):
    if dimension=='visual':return {'approved_design','candidate_runtime'} if mode=='reskin' else {'original_runtime','candidate_runtime'}
    if dimension in ('runtime','platform'):return {'candidate_runtime'}
    if dimension=='performance':return {'test_report','candidate_runtime'}
    return {'test_report'}

def record_verification(case_dir,dimension,status,evidence_ids,note,revision_id=None):
    root=locate(case_dir)
    if modern(root):
        from .case_revisions import record
        return record(case_dir,dimension,status,evidence_ids,note,revision_id)
    with locked(root):
        case=load_case(root);check_source(case);records=evidence_records(root,case)
        if len(evidence_ids)!=len(set(evidence_ids)) or any(x not in records for x in evidence_ids):raise GreaError('INVALID_EVIDENCE_REFERENCE','Evidence IDs must be unique existing records in this case.')
        if dimension in case['required_dimensions'] and status=='not_applicable':raise GreaError('REQUIRED_DIMENSION','Cannot exempt an already-required dimension in a verdict.')
        if status=='passed':
            required=required_kinds(case['mode'],dimension);actual={records[x]['kind'] for x in evidence_ids}
            if not required<=actual:raise GreaError('INSUFFICIENT_EVIDENCE','Passed verdict lacks required evidence roles.',details={'required':sorted(required),'provided':sorted(actual)},next_action='Register relevant original/candidate evidence; static output alone is not runtime proof.')
        value={'case_id':case['case_id'],'dimension':dimension,'status':status,'evidence_ids':evidence_ids,'note':note,'created_at':now(),'order_ns':next_order(root,'verifications','vr_'),'nonce':uuid.uuid4().hex,'authority':'reviewer_assertion'}
        value['id']='vr_'+digest(value);write_new(root/'verifications'/f"{value['id']}.json",value)
    return {'verification':value,'executed_tests':False}

def case_status(case_dir,revision_id=None,max_hash_bytes=8*1024**3):
    root=locate(case_dir)
    if modern(root):
        from .case_revisions import status
        return status(case_dir,revision_id,max_hash_bytes)
    with audit_hashes(max_hash_bytes) as audit:
        result = _legacy_status(root)
        result['hash_coverage'] = 'legacy_source_and_all_evidence_artifacts'
        result['hash_audit'] = audit_report(audit)
        return result

def _legacy_status(root):
    with locked(root, write=False):
        case=load_case(root);check_source(case);records=evidence_records(root,case);latest={}
        if (root/'verifications').is_symlink():raise GreaError('TAMPERED_EVIDENCE','Verification directory is a symlink.')
        history=sorted((read_record(p,'vr_') for p in (root/'verifications').glob('*.json')),key=lambda x:(x['order_ns'],x['id']))
        for value in history:
            if value['case_id']!=case['case_id'] or any(x not in records for x in value['evidence_ids']):raise GreaError('INVALID_VERIFICATION','Verification refers to another case or missing evidence.')
            # Revalidate roles when reading; rehashed forged pass still cannot replace runtime evidence.
            if value['status']=='passed' and not required_kinds(case['mode'],value['dimension'])<={records[x]['kind'] for x in value['evidence_ids']}:
                raise GreaError('INSUFFICIENT_EVIDENCE','Stored verdict has insufficient evidence roles.')
            latest[value['dimension']]=value
        verdicts={dim:latest.get(dim,{'status':'not_run','evidence_ids':[]}) for dim in case['required_dimensions']}
        missing=[d for d,v in verdicts.items() if v['status']!='passed']
        return {'case_id':case['case_id'],'source_integrity':'matched','evidence_count':len(records),'dimensions':verdicts,'missing_or_failed':missing,'declared_acceptance':'legacy_unbound' if not missing else 'incomplete','verified_game_equivalence':False,'history_count':len(history),'limitations':['Verdicts and evidence roles are reviewer assertions, not grea-executed gameplay or visual judgments.','Legacy v1 records are unbound to a candidate. Start a revision before using them for current acceptance.']}
