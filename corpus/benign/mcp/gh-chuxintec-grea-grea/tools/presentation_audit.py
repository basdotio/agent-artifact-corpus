"""Finite observation checks. Component references are not a rendering proof."""
import argparse
import re
from grea.host.paths import Path
import sys
from grea.data_io import load, encode
from grea.safe_paths import disjoint


def inspect(document):
    required={'schema_version','candidate_sha256','run_instance','frames'}
    if not isinstance(document,dict) or set(document)!=required or document['schema_version']!=1 or not document['run_instance']:
        raise ValueError('Closed observation v1 with run identity required')
    if not isinstance(document['candidate_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',document['candidate_sha256']):
        raise ValueError('Candidate SHA-256 required')
    frames=document['frames']
    if not isinstance(frames,list) or not 2<=len(frames)<=10000: raise ValueError('At least two bounded frames required')
    findings=[]; previous={}; frame_id=-1; phases=set(); observed=0
    for frame in frames:
        if set(frame)!={'frame','phase','nodes'} or type(frame['frame']) is not int or frame['frame']<=frame_id:
            raise ValueError('Strictly increasing frames required')
        frame_id=frame['frame']; phase=frame['phase']
        if phase not in ('cold_open','active','closed','reopen','pool_reuse'): raise ValueError('Explicit lifecycle phase required')
        phases.add(phase); seen=set()
        if not isinstance(frame['nodes'],list) or len(frame['nodes'])>10000: raise ValueError('Node budget exceeded')
        for node in frame['nodes']:
            if not isinstance(node,dict) or not {'id','active'} <= set(node) or not isinstance(node['id'],str) or type(node['active']) is not bool:
                raise ValueError('Node identity and actual active state required')
            observed+=1
            identity=node['id']
            if identity in seen: raise ValueError('Duplicate observed identity')
            seen.add(identity)
            def add(code): findings.append(dict(code=code,frame=frame_id,node=identity))
            if node['active']:
                if node.get('culled') is True: add('ACTIVE_GRAPHIC_CULLED')
                # Additive/PMA can contribute RGB even when alpha is zero.
                if node.get('blend')=='alpha' and node.get('effective_alpha')==0: add('ZERO_ALPHA_GRAPHIC')
                if node.get('text_observed',True) and node.get('text_length',0)>0 and node.get('mesh_vertices')==0: add('TEXT_WITHOUT_MESH')
                if node.get('expected_clickable') is True and node.get('raycast_top') is False: add('CLICK_TARGET_OBSTRUCTED')
                if node.get('expected_mask') is True and node.get('mask_count')==0: add('EXPECTED_MASK_MISSING')
                if node.get('callback_generation') is not None and node.get('generation') is not None and node['callback_generation']!=node['generation']:
                    add('STALE_LIFETIME_CALLBACK')
                old=previous.get(identity)
                if phase=='pool_reuse' and node.get('expected_restart') is True and node.get('track_observed',True) and old and old.get('track_observed',True) and node.get('track_time') is not None and old.get('track_time') is not None and node['track_time']>=old['track_time']:
                    add('POOL_RESTART_NOT_OBSERVED')
            previous[identity]=node
    if not observed: raise ValueError('Empty observation coverage')
    return dict(schema_version=1,tool='presentation_audit',status='needs_review' if findings else 'no_findings_in_observed_scope',
                candidate_sha256=document['candidate_sha256'],run_instance=document['run_instance'],phases=sorted(phases),
                lifecycle_coverage=all(p in phases for p in ('cold_open','closed','reopen')), findings=findings,
                scope='Declared observations only; unknown blend, absent counters, unobserved tracks/input and final pixels remain unverified')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        data,digest=load(args.input,max_bytes=32*1024*1024,max_nodes=1000000)
        report=inspect(data);report['input_sha256']=digest
        out=disjoint(args.output,args.input);out.parent.mkdir(parents=True,exist_ok=True)
        with out.open('xb') as stream:stream.write(encode(report))
        print(encode(report).decode());return 1 if report['findings'] else 0
    except (OSError,ValueError,TypeError,KeyError) as error:
        print(str(error),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
