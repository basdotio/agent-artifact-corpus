"""Offline declared evidence closure; never a downloader or server completeness verdict."""
import argparse
from collections import Counter
import json
from grea.host.paths import Path
import re
import sys
from grea.safe_paths import relative_name,unique_paths
from grea.tools._artifact_common import inventory,write_report,validate_output
from grea.data_io import load, sha, encode

LAYERS=('source','cache','cdn','chunk','export','build','capture')
ADAPTERS=('flat-v1','layers-v1')


def rows(document,adapter):
    if not isinstance(document,dict) or type(document.get('schema_version')) is not int or document['schema_version']!=1 or not isinstance(document.get('scope'),str) or not document['scope']:raise ValueError('Versioned manifest with explicit scope required')
    if adapter=='flat-v1':
        if set(document)!={'schema_version','scope','entries'}:raise ValueError('Closed flat manifest required')
        entries=document['entries']
    elif adapter=='layers-v1':
        if set(document)!={'schema_version','scope','layers'} or not isinstance(document['layers'],dict):raise ValueError('Closed layered manifest required')
        entries=[]
        for layer,values in document['layers'].items():
            if layer not in LAYERS or not isinstance(values,list):raise ValueError('Unknown layer')
            for value in values:
                if not isinstance(value,dict) or 'layer' in value and value['layer']!=layer:raise ValueError('Conflicting layer')
                entries.append(dict(value,layer=layer))
    else:raise ValueError('Unsupported manifest adapter')
    if not isinstance(entries,list) or not 1<=len(entries)<=100000:raise ValueError('Expected 1..100000 declared entries')
    result=[];paths=[]
    for row in entries:
        if not isinstance(row,dict) or set(row)-{'id','layer','variant','path','bytes','sha256','payload'} or not isinstance(row.get('id'),str) or not 1<=len(row['id'])<=512 or row.get('layer') not in LAYERS:raise ValueError('Invalid entry identity/layer')
        if not isinstance(row.get('variant',''),str) or len(row.get('variant',''))>128:raise ValueError('Invalid variant')
        if type(row.get('payload',True)) is not bool:raise ValueError('Explicit payload bool required')
        value=dict(row,variant=row.get('variant',''),payload=row.get('payload',True))
        if not value['payload']:
            if any(row.get(k) is not None for k in ('path','bytes','sha256')):raise ValueError('No-payload declarations cannot name a file')
        else:
            value['path']=relative_name(row.get('path')).as_posix();paths.append(value['path'])
            if row.get('bytes') is not None and (type(row['bytes']) is not int or not 0<=row['bytes']<=64*1024**3):raise ValueError('Invalid byte count')
            if row.get('sha256') is not None and not re.fullmatch('[0-9a-f]{64}',row['sha256']):raise ValueError('Invalid digest')
        result.append(value)
    unique_paths(paths)
    return result


def verify(root,document,adapter,previous=None,previous_adapter='flat-v1'):
    root=Path(root).absolute()
    if not root.is_dir() or any(p.is_symlink() for p in (root,*root.parents)):raise ValueError('Regular explicit root without links required')
    declared=rows(document,adapter);files=[];total=0
    for file in root.rglob('*'):
        if file.is_symlink():raise ValueError('Evidence symlink refused')
        if file.is_file():
            files.append(file);total+=file.stat().st_size
            if len(files)>100000 or total>64*1024**3:raise ValueError('Inventory budget exceeded')
        elif not file.is_dir():raise ValueError('Nonregular evidence')
    # Existing inventory supplies streaming hashing and per-file mutation detection.
    actual=inventory(root);unique_paths(actual)
    identities=Counter((x['layer'],x['id'],x['variant']) for x in declared)
    duplicates=[dict(layer=k[0],id=k[1],variant=k[2],count=n) for k,n in sorted(identities.items()) if n>1]
    payloads=[x for x in declared if x['payload']];expected={x['path']:x for x in payloads};missing=sorted(set(expected)-set(actual));extra=sorted(set(actual)-set(expected));changed=[];unverified=[];verified=[]
    for path,row in expected.items():
        if row.get('bytes') is None or row.get('sha256') is None:unverified.append(path)
        elif path in actual:
            if actual[path]!={k:row[k] for k in ('bytes','sha256')}:changed.append(path)
            else:verified.append(path)
    previous_changes=[]
    manifest_diff = dict(added=[], removed=[], modified=[], moved=[], scope_changed=False)
    if previous is not None:
        old=rows(previous,previous_adapter);old_index={(x['layer'],x['id'],x['variant']):x for x in old}
        if len(old_index) != len(old):
            raise ValueError('Previous manifest has duplicate identities')
        current_index = {(x['layer'],x['id'],x['variant']):x for x in declared}
        for identity in sorted(set(old_index) | set(current_index)):
            before, after = old_index.get(identity), current_index.get(identity)
            item = dict(layer=identity[0], id=identity[1], variant=identity[2])
            if before is None:
                manifest_diff['added'].append(item)
            elif after is None:
                manifest_diff['removed'].append(item)
            elif any(before.get(k) != after.get(k) for k in ('path','bytes','sha256','payload')):
                kind = 'moved' if before.get('path') != after.get('path') and all(before.get(k) == after.get(k) for k in ('bytes','sha256','payload')) else 'modified'
                manifest_diff[kind].append(dict(item, before=before, after=after))
            else:
                continue
            previous_changes.append(item)
        manifest_diff['scope_changed'] = previous['scope'] != document['scope']
    closure_failed = bool(missing or extra or changed or unverified or duplicates)
    findings = closure_failed or bool(previous_changes) or manifest_diff['scope_changed']
    return dict(schema_version=1,tool='evidence_manifest',implementation_version='0.2.0',status='needs_review' if findings else 'declared_closure_verified',current_closure='incomplete' if closure_failed else 'verified',manifest_diff=manifest_diff,scope=document['scope'],adapter=adapter,manifest_sha256=sha(encode(document)),previous_manifest_sha256=sha(encode(previous)) if previous is not None else None,counts=dict(declared=len(declared),payloads=len(payloads),no_payload=len(declared)-len(payloads),actual_files=len(actual),verified=len(verified),unverified=len(unverified)),missing=missing,extra=extra,changed=sorted(changed),unverified=sorted(unverified),duplicate_identities=duplicates,changed_since_previous=previous_changes,layer_counts=dict(Counter(x['layer'] for x in declared)),actual=actual,server_completeness_proven=False,parse_import_render_gameplay='not_run',limits=['Only the explicit frozen manifest union is checked. No network, private cache discovery, content parsing, native import, rendering or server completeness is established.','No-payload entries are explicit caller declarations, not independently proven engine semantics.','Per-file fingerprints are not an atomic filesystem snapshot.','Manifest changes require scope review; a changed manifest is not necessarily invalid.'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--adapter',choices=ADAPTERS,required=True);p.add_argument('--previous',type=Path);p.add_argument('--previous-adapter',choices=ADAPTERS,default='flat-v1');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:
        sources=[a.root,a.manifest]+([a.previous] if a.previous else []);validate_output(a.output,sources);document,_=load(a.manifest,32*1024*1024,2000000);previous=load(a.previous,32*1024*1024,2000000)[0] if a.previous else None;r=verify(a.root,document,a.adapter,previous,a.previous_adapter);write_report(r,a.output,sources);print(json.dumps(dict(status=r['status'],report=str(a.output))));return 1 if r['status']=='needs_review' else 0
    except (OSError,ValueError,TypeError,KeyError,RecursionError) as e:print(str(e),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
