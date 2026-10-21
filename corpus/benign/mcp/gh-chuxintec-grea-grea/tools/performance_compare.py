"""Compare measured runs only when workload and measurement conditions match."""
import argparse
import csv
import io
import math
import re
from grea.host.paths import Path
import sys
from grea.data_io import load, encode, sha
from grea.safe_paths import disjoint

CONDITIONS = ('workload_sha256','device','platform','viewport','quality','seed','input_sha256','measurement')


def sample_summary(run):
    if set(run) != {'schema_version','identity','candidate_sha256','samples','counters'} or run['schema_version']!=1:
        raise ValueError('Expected closed performance run v1')
    identity = run['identity']
    if set(identity)!=set(CONDITIONS) or any(identity[k] is None or identity[k]=='' for k in CONDITIONS):
        raise ValueError('All workload and measurement identities are required')
    if not isinstance(run['candidate_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',run['candidate_sha256']):
        raise ValueError('Candidate SHA-256 required')
    samples = run['samples']
    if not isinstance(samples,list) or not 2<=len(samples)<=100000: raise ValueError('Expected 2..100000 samples')
    groups = {}
    previous=-1
    for sample in samples:
        if set(sample)!={'frame','phase','focused','valid','frame_ms'} or type(sample['frame']) is not int or sample['frame']<=previous:
            raise ValueError('Strictly increasing frame identity required')
        previous=sample['frame']
        if sample['phase'] not in ('cold','warmup','steady'): raise ValueError('Explicit phase required')
        if sample['valid'] is not True or sample['focused'] is not True: raise ValueError('Invalid/background samples cannot support an optimization claim')
        ms=sample['frame_ms']
        if type(ms) not in (int,float) or not math.isfinite(ms) or ms<=0: raise ValueError('Positive finite measured frame time required')
        groups.setdefault(sample['phase'],[]).append(ms)
    summary={}
    for phase, values in groups.items():
        values.sort()
        summary[phase]=dict(count=len(values),mean=sum(values)/len(values),p50=values[math.ceil(len(values)*.50)-1],p95=values[math.ceil(len(values)*.95)-1],p99=values[math.ceil(len(values)*.99)-1])
    if 'steady' not in summary or summary['steady']['count']<2: raise ValueError('At least two steady samples required')
    counters = run['counters']
    if not isinstance(counters,dict): raise ValueError('Counter status map required')
    for name, counter in counters.items():
        if not isinstance(counter,dict) or set(counter)!={'supported','value','unit'} or type(counter['supported']) is not bool:
            raise ValueError('Explicit counter validity required')
        value=counter['value']
        if not counter['supported'] and value is not None: raise ValueError('Unsupported counter is null, not zero')
        if counter['supported'] and (type(value) not in (int,float) or not math.isfinite(value)): raise ValueError('Measured finite counter value required')
    return summary


def compare(before,after):
    a,b=sample_summary(before),sample_summary(after)
    differences=[k for k in CONDITIONS if before['identity'][k]!=after['identity'][k]]
    if differences: raise ValueError('Incomparable workload/conditions: '+', '.join(differences))
    if {p:v['count'] for p,v in a.items()}!={p:v['count'] for p,v in b.items()}:
        raise ValueError('Phase sample coverage differs')
    return dict(schema_version=1,status='comparable',before_sha256=before['candidate_sha256'],after_sha256=after['candidate_sha256'],
                identity=before['identity'],before=a,after=b,
                steady_delta_percent={metric:100*(b['steady'][metric]/a['steady'][metric]-1) for metric in ('mean','p50','p95','p99')},
                counters={'before':before['counters'],'after':after['counters']},
                scope='Measured workload only; no gameplay, visual quality, statistical significance or target FPS claim')


def read_run(path, metadata=None):
    if metadata is None:
        return load(path,max_bytes=32*1024*1024,max_nodes=1000000)
    context, metadata_sha=load(metadata)
    if set(context)!={'schema_version','identity','candidate_sha256','counters'}:
        raise ValueError('CSV metadata must contain only run identity and counter declarations')
    from grea.common import hash_file
    identity=hash_file(path,max_bytes=32*1024*1024)
    raw=Path(path).read_bytes()
    if sha(raw)!=identity['sha256']: raise ValueError('CSV changed during read')
    reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    if reader.fieldnames!=['frame','phase','focused','valid','frame_ms']:
        raise ValueError('Only explicit normalized performance CSV v1 columns are supported')
    samples=[]
    for row in reader:
        if len(samples)>=100000 or row['focused'] not in ('true','false') or row['valid'] not in ('true','false'):
            raise ValueError('Invalid CSV boolean or row budget')
        samples.append(dict(frame=int(row['frame']),phase=row['phase'],focused=row['focused']=='true',valid=row['valid']=='true',frame_ms=float(row['frame_ms'])))
    context['samples']=samples
    return context,sha(encode({'csv':identity['sha256'],'metadata':metadata_sha}))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before',type=Path,required=True);parser.add_argument('--after',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--before-metadata',type=Path);parser.add_argument('--after-metadata',type=Path)
    args=parser.parse_args(argv)
    try:
        before,a=read_run(args.before,args.before_metadata)
        after,b=read_run(args.after,args.after_metadata)
        report=compare(before,after);report['inputs']={'before':a,'after':b}
        out=disjoint(args.output,args.before,args.after);out.mkdir(parents=True,exist_ok=False)
        (out/'report.json').write_bytes(encode(report))
        with (out/'summary.csv').open('x',newline='') as stream:
            writer=csv.writer(stream);writer.writerow(['phase','metric','before','after'])
            for phase in report['before']:
                for metric in ('count','mean','p50','p95','p99'):
                    writer.writerow([phase,metric,report['before'][phase][metric],report['after'][phase][metric]])
        print(encode(report).decode());return 0
    except (OSError,ValueError,KeyError,TypeError) as error:
        print(str(error),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
