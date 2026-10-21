"""Verify an explicit Mono build identity, then read DLL metadata with pinned Cecil.

No Editor-loaded types or inspected assembly code are executed. IL2CPP is unsupported.
"""
import argparse
import hashlib
import json
import os
from grea.host.paths import Path
import re
import shutil
import subprocess
import sys
from grea.safe_paths import canonical_path, disjoint, relative_name, unique_paths
from grea.native_exit_contracts import MAX_PLAYER_ASSEMBLIES

ROOT=Path(__file__).resolve().parents[3]
READER=ROOT/'tools/unity/assembly-audit/bin/Release/net8.0/Grea.AssemblyAudit.dll'

class AuditError(ValueError):
    def __init__(self,code,message):super().__init__(message);self.code=code

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def reject(code,message):raise AuditError(code,message)


def audit(manifest,managed,policy):
    manifest=canonical_path(manifest);managed=canonical_path(managed)
    if manifest.stat().st_size>1024*1024:reject('MANIFEST_BUDGET','Manifest exceeds 1 MiB')
    identity=json.loads(manifest.read_bytes())
    if not isinstance(identity,dict):reject('INVALID_MANIFEST','Expected a manifest object')
    if identity.get('backend')!='Mono':reject('UNSUPPORTED_BACKEND','Only managed Mono DLLs are inspected; IL2CPP is not clean by absence')
    if identity.get('schema_version')!=1 or not all(isinstance(identity.get(k),str) and identity[k] for k in ('build_id','platform')) or not isinstance(identity.get('source_sha256'),str) or not re.fullmatch('[0-9a-f]{64}',identity.get('source_sha256','')):reject('INVALID_MANIFEST','Build ID, source SHA, platform and backend are required')
    from grea.native_exit_contracts import documents
    from jsonschema import Draft202012Validator
    schemas=documents()
    if list(Draft202012Validator(schemas['unity-player-manifest.schema.json']).iter_errors(identity)):reject('INVALID_MANIFEST','Manifest does not match the versioned schema')
    if list(Draft202012Validator(schemas['unity-player-policy.schema.json']).iter_errors(policy)):reject('INVALID_POLICY','Policy does not match the versioned schema')
    if not isinstance(policy,dict) or policy.get('schema_version')!=1 or set(policy)-{'schema_version','required_types','forbidden_types','forbidden_references','forbidden_assemblies','call_types'}:reject('INVALID_POLICY','Use versioned explicit type/reference checks; no implicit waivers')
    for key in ('required_types','forbidden_types','forbidden_references','forbidden_assemblies','call_types'):
        values=policy.get(key,[])
        if not isinstance(values,list) or len(values)>256 or not all(isinstance(x,str) and 0<len(x)<1024 for x in values):reject('INVALID_POLICY','Expected bounded explicit identity lists')
    if not policy.get('required_types'):reject('INVALID_POLICY','At least one required project type is necessary; zero project types must not pass')
    inputs=identity.get('assemblies')
    if not isinstance(inputs,list) or not 1<=len(inputs)<=MAX_PLAYER_ASSEMBLIES:reject('INVALID_MANIFEST',f'Select 1..{MAX_PLAYER_ASSEMBLIES} exact managed DLLs')
    names=[];total=0
    for row in inputs:
        if not isinstance(row,dict) or set(row)!={'path','sha256'} or not isinstance(row['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',row['sha256']):reject('INVALID_MANIFEST','Each DLL requires a relative path and SHA')
        rel=relative_name(row['path']);names.append(rel)
        if rel.suffix.lower()!='.dll':reject('INVALID_MANIFEST','Only explicit DLL inputs')
        path=managed/rel
        if any(p.is_symlink() for p in (path,*path.parents)) or managed not in path.resolve().parents or not path.is_file():reject('UNSAFE_INPUT','Missing or linked DLL')
        size=path.stat().st_size;total+=size
        if size>64*1024*1024 or total>512*1024*1024:reject('ASSEMBLY_BUDGET','DLL byte budget exceeded')
        if sha(path)!=row['sha256']:reject('SOURCE_IDENTITY_MISMATCH','DLL does not match build manifest')
    unique_paths(names)
    actual={p.name for p in managed.iterdir() if p.is_file() and p.suffix.lower()=='.dll'}
    if {str(n) for n in names}!=actual:reject('PAYLOAD_SET_MISMATCH','Manifest must enumerate every immediate managed DLL; missing/extra files cannot pass')
    if not READER.is_file() or not shutil.which('dotnet'):reject('READER_UNAVAILABLE','Build the optional locked Cecil provider first; see docs/providers/unity-native-exit.md')
    lock=json.loads((ROOT/'tools/unity/assembly-audit/cecil-lock.json').read_text(encoding='utf-8'))
    cecil=READER.parent/'Mono.Cecil.dll'
    if not cecil.is_file() or sha(cecil)!=lock['sha256']:reject('READER_DEPENDENCY_IDENTITY','Cecil provider does not match its pinned binary identity')
    env={k:v for k,v in os.environ.items() if not k.startswith(('DOTNET_STARTUP_HOOKS','CORECLR_PROFILER','CORECLR_ENABLE_PROFILING','COR_PROFILER','COR_ENABLE_PROFILING','DOTNET_ADDITIONAL_DEPS','DOTNET_SHARED_STORE'))}
    try: completed=subprocess.run(['dotnet',str(READER),str(manifest),str(managed),json.dumps(policy.get('call_types',[]))],capture_output=True,timeout=60,env=env)
    except subprocess.TimeoutExpired:reject('READER_TIMEOUT','Metadata reader exceeded 60 seconds')
    if len(completed.stdout)>32*1024*1024:reject('REPORT_BUDGET','Metadata report exceeds 32 MiB')
    try: data=json.loads(completed.stdout)
    except (ValueError,UnicodeError):reject('READER_FAILED','Reader did not return a valid metadata report')
    if completed.returncode or data.get('error'):reject('METADATA_READ_ERROR',str(data.get('error','Reader process failed')))
    for row in data['assemblies']:
        expected=next(x for x in inputs if x['path']==row['path'])
        if expected['sha256']!=row['sha256'] or sha(managed/row['path'])!=row['sha256']:reject('SOURCE_CHANGED','Assembly bytes changed during metadata read')
    types={t['name'] for a in data['assemblies'] for t in a['types']};refs={r for a in data['assemblies'] for r in a['references']}
    findings=[]
    for key,observed,missing in [('required_types',types,True),('call_types',types,True),('forbidden_types',types,False),('forbidden_references',refs,False),('forbidden_assemblies',{a['name'] for a in data['assemblies']},False)]:
        for name in policy.get(key,[]):
            violates=(name not in observed) if missing else (name in observed)
            if violates:findings.append(dict(check=key,identity=name))
    return dict(schema_version=1,tool='unity_player_audit',implementation_version='0.1.1',status='fail' if findings else 'metadata_checks_passed',
        source_format='Mono-managed-assemblies',build_identity=identity,manifest_sha256=sha(manifest),policy=policy,
        reader=dict(sha256=sha(READER),cecil_dll_sha256=sha(cecil),cecil_lock_sha256=sha(ROOT/'tools/unity/assembly-audit/packages.lock.json')),
        assemblies=data['assemblies'],findings=findings,errors=[],unsupported=[],scope='Selected metadata checks only; no executed-call graph, gameplay, stripping completeness or source provenance attestation',
        evidence_layers=dict(static_source='not_run',editor='not_run',actual_player_metadata='read'),
        limits=['Manifest build/source/platform are caller-declared; every immediate DLL digest and set are verified.',
                'Only explicit call_types emit call/callvirt/newobj sites; these are metadata, not proof of execution.',
                'Type identities are exact; mechanisms and renamed implementations still require structural/human review.',
                'No inspected DLL is loaded into CLR; no symbols, custom-attribute resolution or assembly resolution.'],effects=['filesystem_read','explicit_output_write','metadata_reader_process'])


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--managed',type=Path,required=True);p.add_argument('--policy',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv)
    try:
        output=disjoint(a.output,a.managed,a.manifest,a.policy)
        if output.exists():reject('OUTPUT_EXISTS','Output must be a new file')
        if a.policy.stat().st_size>1024*1024:reject('POLICY_BUDGET','Policy exceeds 1 MiB')
        result=audit(a.manifest,a.managed,json.loads(a.policy.read_text(encoding='utf-8')))
        with output.open('x') as stream:json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
        print(json.dumps(dict(status=result['status'],report=str(output),findings=len(result['findings']))));return 1 if result['findings'] else 0
    except (ValueError,OSError) as error:
        code=getattr(error,'code','INVALID_INPUT');print(json.dumps(dict(schema_version=1,tool='unity_player_audit',status='unsupported' if code=='UNSUPPORTED_BACKEND' else 'error',errors=[dict(code=code,message=str(error))])));return 1 if code=='UNSUPPORTED_BACKEND' else 2

if __name__=='__main__':sys.exit(main())
