#!/usr/bin/env python3
"""Compatibility diagnostics through grea's single bounded application layer.
Default is presence-only. Version/help probes require --probe and explicit --tool.
"""
import argparse, hashlib, json, re, sys
from pathlib import Path
from grea.common import package_root
ROOT = package_root()
from grea.application import dispatch
from grea.common import write_new

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--tool',action='append',default=[])
    parser.add_argument('--probe',action='store_true')
    parser.add_argument('--verify-frida-pair',action='store_true',help='Explicitly probe Frida and verify the pinned Android server archive; never launch server.')
    args=parser.parse_args(argv)
    selected=list(dict.fromkeys(args.tool+(['frida'] if args.verify_frida_pair else [])))
    request={'probe':args.probe or args.verify_frida_pair}
    if selected:request['tool_ids']=selected
    report=dispatch('doctor',request)
    if args.verify_frida_pair and report['result'] is not None:
        readme=(ROOT/'docs/providers/Frida接入.md').read_text()
        version=re.search(r'with `frida` ([\d.]+)',readme)
        archive=ROOT/'.private/providers/frida'/f'frida-server-{version[1] if version else "missing"}-android-arm64.xz'
        client=next((x for x in report['result']['checks'] if x['tool_id']=='frida'),{})
        matched=bool(version and archive.is_file() and version[1] in client.get('output','') and hashlib.sha256(archive.read_bytes()).hexdigest() in readme)
        report['result']['frida_pair']={'matched':matched,'server_executed':False}
        if not matched and report['status']=='ok':report['status']='partial'
    if args.output:write_new(args.output,report)
    if args.json:print(json.dumps(report,ensure_ascii=False,indent=2))
    else:
        print('grea doctor:',report['status'])
        for row in (report['result'] or {}).get('checks',[]):print(row['tool_id'],row['state'])
        if report['error']:print(report['error']['code'],report['error']['message'])
    return {'ok':0,'partial':1,'error':2}[report['status']]
if __name__=='__main__':raise SystemExit(main())
