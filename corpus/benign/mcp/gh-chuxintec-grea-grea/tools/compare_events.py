#!/usr/bin/env python3
"""Validate event traces then delegate exact comparison to the central tools implementation.
Schema: one JSON object per line: seq (integer), event (nonempty string), state (object).
Optional time/rng fields may be compared with additional --field options.
"""
import argparse,json,sys
from pathlib import Path
def validate(path):
    previous=None;count=0
    with path.open() as f:
        for line in f:
            if not line.strip():continue
            row=json.loads(line)
            if not isinstance(row,dict) or type(row.get('seq')) is not int or not isinstance(row.get('event'),str) or not row['event'] or not isinstance(row.get('state'),dict):raise ValueError('Invalid event schema')
            if previous is not None and row['seq']<=previous:raise ValueError('seq must increase')
            previous=row['seq'];count+=1
    if not count:raise ValueError('Empty trace')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('reference',type=Path);p.add_argument('candidate',type=Path);p.add_argument('--field',action='append',default=[])
    a=p.parse_args()
    try:
        for path in [a.reference,a.candidate]:validate(path)
    except (OSError,ValueError) as e:p.error(str(e))
    from grea.tools.compare_traces import main as compare_main
    cmd=[str(a.reference),str(a.candidate)]
    for field in ['/seq','/event','/state']+a.field:cmd+=['--field',field]
    return compare_main(cmd)
if __name__=='__main__':raise SystemExit(main())
