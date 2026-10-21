"""Conservative native-exit source inventory; source/Editor/Player are separate gates.

A missing or renamed known mechanism is never a static native-pass certificate.
"""
import argparse
import hashlib
import json
import os
from grea.host.paths import Path
import re
import sys
from grea.safe_paths import canonical_path, disjoint, relative_name
from grea.tools.unity_dependency_audit import audit as dependency_audit, within

MECHANISMS=('full_source_graph','source_identity_binding','source_lifecycle','dynamic_configuration','source_animation','source_resource_catalog')
LITERALS=re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|@"(?:[^"]|"")*"|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
DYNAMIC=re.compile(r'\b(?:Resources\s*\.\s*(?:Load|LoadAll)|Assembly\s*\.\s*Load|Type\s*\.\s*GetType|GetMethod|GetField|Activator\s*\.\s*CreateInstance)\b')

def code_only(text):
    return LITERALS.sub(lambda m:re.sub(r'[^\n]',' ',m.group()),text)


def inspect(project,roots,policy,max_files=10000,max_bytes=64*1024*1024):
    project=canonical_path(project);assets=project/'Assets'
    if not assets.is_dir() or assets.is_symlink():raise ValueError('Expected an explicit project with regular Assets')
    if not isinstance(policy,dict) or set(policy)!={'schema_version','exits'} or policy['schema_version']!=1 or not isinstance(policy['exits'],list) or len(policy['exits'])>256:raise ValueError('Expected versioned exit policy, without waivers')
    from grea.native_exit_contracts import documents
    from jsonschema import Draft202012Validator
    if list(Draft202012Validator(documents()['unity-native-exit-policy.schema.json']).iter_errors(policy)):raise ValueError('Exit policy does not match versioned schema')
    seen=set()
    for item in policy['exits']:
        if not isinstance(item,dict) or set(item)!={'id','relative_path','symbol','mechanism','reason'} or not all(isinstance(x,str) and x for x in item.values()):raise ValueError('Every exit needs id/path/symbol/mechanism/reason; allow/waiver flags are invalid')
        rel=relative_name(item['relative_path'])
        if rel.parts[0]!='Assets' or rel.suffix!='.cs' or item['mechanism'] not in MECHANISMS or not re.fullmatch(r'[A-Za-z_]\w*',item['symbol']):raise ValueError('Invalid exit path, mechanism or symbol')
        if item['id'] in seen:raise ValueError('Duplicate exit identity')
        seen.add(item['id'])
    if not roots:raise ValueError('At least one explicit build root is required')
    roots=[within(assets,value) for value in roots]
    paths=[];issues=[];total=0
    for base,dirs,files in os.walk(assets,followlinks=False):
        linked=[x for x in dirs if (Path(base)/x).is_symlink()]
        issues.extend(dict(kind='symlink_directory_unscanned',path=str((Path(base)/x).relative_to(project))) for x in linked)
        dirs[:]=sorted(x for x in dirs if x not in linked)
        for name in sorted(files):
            path=Path(base)/name
            if path.is_symlink():issues.append(dict(kind='symlink_file_unscanned',path=str(path.relative_to(project))));continue
            paths.append(path)
            if len(paths)>max_files:raise ValueError('File inventory budget exceeded')
            if path.suffix in ('.cs','.asmdef','.asmref'):
                size=path.stat().st_size;total+=size
                if size>2*1024*1024 or total>max_bytes:raise ValueError('Source text budget exceeded')
    resources=[p.relative_to(assets).as_posix() for p in paths if 'Resources' in p.relative_to(assets).parts and 'Editor' not in p.relative_to(assets).parts and p.suffix!='.meta']
    roots=sorted(set(roots+resources))
    definitions={};assembly_rows=[]
    for path in paths:
        if path.suffix!='.asmdef':continue
        row=json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(row,dict) or not isinstance(row.get('name'),str):raise ValueError('Invalid asmdef shape')
        if path.parent in definitions:issues.append(dict(kind='multiple_asmdefs',path=str(path.relative_to(project))))
        definitions[path.parent]=row
        assembly_rows.append(dict(path=path.relative_to(project).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),definition=row))
    def assembly(path):
        for directory in (path.parent,*path.parents):
            definition=definitions.get(directory)
            if definition:
                editor=set(definition.get('includePlatforms',[]))=={'Editor'} or 'TestAssemblies' in definition.get('optionalUnityReferences',[])
                return definition.get('name','unnamed asmdef'),not editor
            if directory==assets:break
        if 'Editor' in path.relative_to(assets).parts:return 'Editor-path candidate',False
        return 'Assembly-CSharp candidate',True
    sources={};dynamic=[];structural=[]
    for path in paths:
        if path.suffix=='.asmref':issues.append(dict(kind='asmref_requires_editor',path=path.relative_to(project).as_posix()))
        if path.suffix!='.cs':continue
        raw=path.read_text(encoding='utf-8-sig');code=code_only(raw);name,candidate=assembly(path);rel=path.relative_to(project).as_posix()
        row=dict(path=rel,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),assembly_candidate=name,player_source_candidate=candidate)
        sources[rel]=(row,code)
        if not candidate:continue
        for match in DYNAMIC.finditer(code):dynamic.append(dict(path=rel,line=code.count('\n',0,match.start())+1,kind='computed_or_reflective_access_requires_review'))
        # Deliberately a review hint, not a mechanism verdict: legal DTOs may share this shape.
        if re.search(r'\bDictionary\s*<\s*string\s*,\s*object\s*>',code) and re.search(r'\b(?:Invoke|Update|Start|LateUpdate)\s*\(',code):
            structural.append(dict(path=rel,kind='open_value_map_with_dispatch_or_lifecycle',status='review_required',reason='May be source emulation or a legal bounded service; inspect actual ownership and Player types'))
    exits=[]
    for item in policy['exits']:
        owned=sources.get(item['relative_path']);referrers=[]
        for rel,(row,code) in sources.items():
            if row['player_source_candidate'] and re.search(r'\b'+re.escape(item['symbol'])+r'\b',code):referrers.append(rel)
        present=bool(owned and owned[0]['player_source_candidate'])
        exits.append(dict(item,status='fail' if present or referrers else 'requires_editor_confirmation',player_source_present=present,lexical_reference_candidates=referrers,waiver=False))
    closure=dependency_audit(assets,roots,min(max_bytes,32*1024*1024))
    return dict(schema_version=1,tool='unity_native_exit',implementation_version='0.1.0',source_format='Unity-text-source-candidates',
        status='fail' if any(x['status']=='fail' for x in exits) else 'not_run',native_exit_passed=False,
        roots=roots,source_files=[r for r,_ in sources.values()],assemblies=assembly_rows,exit_registry=exits,dynamic_review_queue=dynamic,
        structural_review_queue=structural,guid_closure=closure,issues=issues,errors=[],unsupported=[],
        evidence_layers=dict(static_source='scanned_candidates_only',editor='not_run',actual_player_metadata='not_run'),
        scope='Explicit Assets source and text-GUID closure; known mechanism exit inventory, never full native maintainability certification',
        limits=['Lexical C# candidates; no semantic binding. Raw/interpolated strings, preprocessors, aliases and overloads require compiled review.',
                'Editor paths/asmdef flags are tentative; asmrefs, UPM, platform/define constraints require CompilationPipeline.',
                'GUID graph is the existing unity_dependency_audit result; binary assets, dynamic/preloaded roots need Editor.',
                'No spelling blacklist for cc/JSON/Spine/IDs. Renamed or removed exits remain requires_editor_confirmation.',
                'No source license, behavior, performance, Player stripping or game parity claim.'],effects=['filesystem_read','explicit_output_write'])


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);p.add_argument('--root',action='append',required=True);p.add_argument('--policy',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv)
    try:
        output=disjoint(a.output,a.project,a.policy)
        if output.exists():raise ValueError('Report already exists')
        if a.policy.stat().st_size>1024*1024:raise ValueError('Policy exceeds 1 MiB')
        report=inspect(a.project,a.root,json.loads(a.policy.read_bytes()))
        with output.open('x') as stream:json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n')
        print(json.dumps(dict(status=report['status'],report=str(output),native_exit_passed=False)));return 1
    except (ValueError,OSError) as error:
        print(json.dumps(dict(schema_version=1,tool='unity_native_exit',status='error',errors=[dict(code='INVALID_INPUT',message=str(error))])));return 2

if __name__=='__main__':sys.exit(main())
