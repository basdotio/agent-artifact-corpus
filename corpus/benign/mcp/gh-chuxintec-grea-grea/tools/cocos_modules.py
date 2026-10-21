"""AST-only module/RF evidence. Requires Node and the separately pinned Acorn provider."""
import argparse
import hashlib
import json
import os
from grea.host.paths import Path
import shutil
import subprocess
import sys
from grea.tools.cocos_assets import ParseError, fail, safe_path, error_report

ROOT=Path(__file__).resolve().parents[3]
ADAPTERS=('browserify-table-v1','define-browserify-v1','define-factory-candidates-v1','system-register-v1')


def index_source(raw,adapter):
    if adapter not in ADAPTERS: fail('UNSUPPORTED_ADAPTER','$','Choose a supported wrapper adapter')
    if len(raw)>32*1024*1024: fail('BUDGET_EXCEEDED','$','Source exceeds 32 MiB')
    node=shutil.which('node')
    if not node: fail('DEPENDENCY_MISSING','$','Node is required for the optional AST provider')
    env={key:value for key,value in os.environ.items() if key not in ('NODE_OPTIONS','NODE_PATH')}
    try:
        result=subprocess.run([node,'--max-old-space-size=256',str(ROOT/'tools/cocos/index-modules.cjs'),adapter],input=raw,
                              capture_output=True,timeout=30,env=env)
    except subprocess.TimeoutExpired: fail('BUDGET_EXCEEDED','$','AST subprocess timed out')
    try: report=json.loads(result.stdout)
    except (ValueError,UnicodeError): fail('AST_PROCESS_FAILED','$','AST provider failed without a valid report; install the pinned dependency')
    if 'error' in report:
        e=report['error'];raise ParseError(e['code'],e['location'],e['message'])
    if result.returncode: fail('AST_PROCESS_FAILED','$','AST provider exited unsuccessfully')
    for module in report['modules']:
        start,end=module['source_bytes']['start'],module['source_bytes']['end']
        if not 0<=start<end<=len(raw) or hashlib.sha256(raw[start:end]).hexdigest()!=module['sha256']: fail('SOURCE_IDENTITY_MISMATCH','$','AST byte-range mismatch')
    return report


def export_index(source,output,adapter):
    source,output=safe_path(source),safe_path(output)
    if output.exists(): fail('OUTPUT_EXISTS',str(output),'Candidate output must be a new directory')
    with source.open('rb') as stream: raw=stream.read(32*1024*1024+1)
    report=index_source(raw,adapter)
    report['source']['name']=source.name
    payloads=[]
    for module in report['modules']:
        data=module.pop('source').encode('utf-8');payloads.append((module['filename'],data))
    from grea.safe_paths import unique_paths
    try: unique_paths([name for name,_ in payloads])
    except ValueError: fail('OUTPUT_NAME_COLLISION','$','Module filenames conflict or are unsafe')
    report['outputs']=[dict(path=name,sha256=hashlib.sha256(data).hexdigest()) for name,data in payloads]
    output.mkdir(parents=True,exist_ok=False)
    for name,data in payloads: (output/name).write_bytes(data)
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--adapter',choices=ADAPTERS,required=True);a=p.parse_args(argv)
    try: report=export_index(a.input,a.output,a.adapter)
    except (ParseError,OSError) as error:
        report=error_report('cocos_modules',a.adapter,error)
        print(json.dumps(report,ensure_ascii=False));return 1 if report['status']=='unsupported' else 2
    print(json.dumps(report,ensure_ascii=False));return 1 if report['status']=='partial' else 0

if __name__=='__main__':sys.exit(main())
