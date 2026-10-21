#!/usr/bin/env python3
"""Probe recovered combined GLES programs; original unchanged, adaptations explicit."""
import argparse,json,re,subprocess,hashlib
from grea.host.paths import Path

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    s=a.source.read_text(encoding='utf-8');results=[]
    for stage,define in [('vert','VERTEX'),('frag','FRAGMENT')]:
     # Retain the conditional branches but put the version directive first.
     body=re.sub(r'^\s*#version[^\n]*','',s,flags=re.M)
     for version,mode in [('300','original-profile'),('310','spirv-adapted')]:
      path=a.output/(stage+'-'+version+'.'+stage);path.write_text('#version '+version+' es\n#define '+define+'\n'+body, encoding='utf-8')
      spv=a.output/(stage+'.spv');cmd=['glslangValidator','-S',stage,str(path)]
      if version=='310':cmd+=['-G','--auto-map-locations','--auto-map-bindings','-o',str(spv)]
      proc=subprocess.run(cmd,capture_output=True,text=True,timeout=60);(a.output/(stage+'-'+version+'.log')).write_text(proc.stdout+proc.stderr, encoding='utf-8')
      results.append({'stage':stage,'mode':mode,'command':cmd,'exit_code':proc.returncode})
      if version=='310' and proc.returncode==0:
       for suffix,opts in [('validate',['spirv-val',str(spv)]),('reflection',['spirv-cross',str(spv),'--reflect']),('hlsl',['spirv-cross',str(spv),'--hlsl','--shader-model','50']),('msl',['spirv-cross',str(spv),'--msl'])]:
        r=subprocess.run(opts,capture_output=True,text=True,timeout=60);(a.output/(stage+'.'+suffix)).write_text(r.stdout+r.stderr, encoding='utf-8');results.append({'stage':stage,'mode':suffix,'exit_code':r.returncode})
    report={'source':str(a.source.resolve()),'sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),'changes':['version hoisted; selected stage macro inserted','SPIR-V branch only: ES300 promoted to310, locations/bindings auto-mapped'],'results':results,'boundary':'Compiler/conversion only, not Unity ShaderLab or rendering equivalence.'};(a.output/'report.json').write_text(json.dumps(report,indent=2), encoding='utf-8');print(json.dumps(report))
    raise SystemExit(0 if all(r['exit_code']==0 for r in results) else 1)

if __name__ == '__main__':
    main()
