"""Project-local immutable baseline, evidence records and explicit reviewer assertions."""
import json,uuid,time,contextlib,tempfile,shutil
from pathlib import Path
from .common import GreaError,hash_file,digest,write_new,now,publish_directory
from .workflows import WORKFLOWS

def locate(path):
    path=Path(path).expanduser()
    if path.name!='.grea':path=path/'.grea'
    if path.is_symlink() or not (path/'case.json').is_file():raise GreaError('CASE_NOT_FOUND','No case at the requested project.',details={'path':str(path)})
    return path.resolve()

def load_case(root):
    value=json.loads((root/'case.json').read_text())
    claim=value.copy();fingerprint=claim.pop('case_id',None)
    if not fingerprint or fingerprint!='case_'+digest(claim):raise GreaError('TAMPERED_CASE','Case baseline digest does not match.')
    return value

@contextlib.contextmanager
def locked(root, write=True):
    try:import fcntl
    except ImportError:raise GreaError('UNSUPPORTED_HOST','Case mutation currently requires POSIX file locking.')
    lock=root/'.lock'
    if lock.is_symlink():raise GreaError('INVALID_CASE','Case lock may not be a symlink.')
    if not lock.is_file():raise GreaError('INVALID_CASE','Case lock file is missing.')
    with lock.open('r') as f:
        fcntl.flock(f.fileno(),fcntl.LOCK_EX if write else fcntl.LOCK_SH)
        try:yield
        finally:fcntl.flock(f.fileno(),fcntl.LOCK_UN)

def check_source(case):
    actual=hash_file(case['source']['path'])
    if actual['sha256']!=case['source']['sha256']:raise GreaError('STALE_SOURCE','The baseline source changed; create a new case.',details={'expected':case['source']['sha256'],'actual':actual['sha256']})

def init_case(project_dir,source,mode,required_dimensions=None):
    project=Path(project_dir).expanduser()
    if project.is_symlink() or not project.is_dir():raise GreaError('INVALID_PROJECT','Choose an existing real project directory.')
    identity=hash_file(source)
    dims=required_dimensions if required_dimensions is not None else WORKFLOWS[mode]['dimensions']
    if not dims or len(dims)!=len(set(dims)):raise GreaError('INVALID_REQUIREMENTS','Required dimensions must be nonempty and unique.')
    root=project.resolve()/'.grea'
    if root.exists() or root.is_symlink():raise GreaError('OUTPUT_EXISTS','Project already has a case; preserve it rather than overwrite.')
    value={'schema_version':1,'created_at':now(),'nonce':uuid.uuid4().hex,'project_dir':str(project.resolve()),'mode':mode,'source':identity,'required_dimensions':dims}
    value['case_id']='case_'+digest(value)
    stage=Path(tempfile.mkdtemp(prefix='.grea-init-',dir=project.resolve()))
    try:
        (stage/'.lock').touch(exist_ok=False)
        (stage/'evidence').mkdir();(stage/'verifications').mkdir()
        write_new(stage/'case.json',value)
        publish_directory(stage,root)
    finally:
        if stage.exists():shutil.rmtree(stage)
    return {'case_dir':str(root),'case':value,'acceptance':'not_run'}

def read_record(path,prefix):
    if path.is_symlink():raise GreaError('TAMPERED_EVIDENCE','Record is a symlink.')
    value=json.loads(path.read_text());body=value.copy();rid=body.pop('id',None)
    if rid!=prefix+digest(body):raise GreaError('TAMPERED_EVIDENCE','Record content does not match its ID.',details={'record':str(path)})
    return value

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

def add_evidence(case_dir,kind,path,description):
    root=locate(case_dir)
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

def record_verification(case_dir,dimension,status,evidence_ids,note):
    root=locate(case_dir)
    with locked(root):
        case=load_case(root);check_source(case);records=evidence_records(root,case)
        if len(evidence_ids)!=len(set(evidence_ids)) or any(x not in records for x in evidence_ids):raise GreaError('INVALID_EVIDENCE_REFERENCE','Evidence IDs must be unique existing records in this case.')
        if dimension in case['required_dimensions'] and status=='not_applicable':raise GreaError('REQUIRED_DIMENSION','Cannot exempt an already-required dimension in a verdict.')
        if status=='passed':
            required=required_kinds(case['mode'],dimension);actual={records[x]['kind'] for x in evidence_ids}
            if not required<=actual:raise GreaError('INSUFFICIENT_EVIDENCE','Passed verdict lacks required evidence roles.',details={'required':sorted(required),'provided':sorted(actual)},next_action='Register relevant original/candidate evidence; static output alone is not runtime proof.')
        value={'case_id':case['case_id'],'dimension':dimension,'status':status,'evidence_ids':evidence_ids,'note':note,'created_at':now(),'order_ns':time.time_ns(),'nonce':uuid.uuid4().hex,'authority':'reviewer_assertion'}
        value['id']='vr_'+digest(value);write_new(root/'verifications'/f"{value['id']}.json",value)
    return {'verification':value,'executed_tests':False}

def case_status(case_dir):
    root=locate(case_dir)
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
        return {'case_id':case['case_id'],'source_integrity':'matched','evidence_count':len(records),'dimensions':verdicts,'missing_or_failed':missing,'declared_acceptance':'ready_for_review' if not missing else 'incomplete','verified_game_equivalence':False,'history_count':len(history),'limitations':['Verdicts and evidence roles are reviewer assertions, not grea-executed gameplay or visual judgments.','Unknown, failed and not-run dimensions do not aggregate to passed.']}
