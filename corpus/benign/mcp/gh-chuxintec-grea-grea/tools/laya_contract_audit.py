#!/usr/bin/env python3
"""Read-only checks of project-local Laya mesh parsers and particle conversion.
Loads explicitly selected Python modules (trusted local code), never auto-imports assets.
"""
import argparse,importlib.util,json,sys
from pathlib import Path

def load(path):
    sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location('laya_audit_adapter',path);m=importlib.util.module_from_spec(spec)
    sys.path.insert(0,str(path.parent));spec.loader.exec_module(m);return m

def check_mesh(m,path,global_skin):
    data=m.mesh(path,global_skin=global_skin);bones=len(data['bones']);vertices=data['vertices']
    for sub in data['submeshes']:
        if any(i<0 or i>=len(vertices) for i in sub['indices']):raise ValueError('Vertex index out of range')
    for v in vertices:
        weights=v.get('BLENDWEIGHT',[]);indices=v.get('BLENDINDICES',[])
        for i,w in zip(indices,weights):
            if w>0 and not 0<=i<bones:raise ValueError('Weighted bone index out of range')
        if global_skin and indices!=v.get('RAW_BLENDINDICES',indices):raise ValueError('Global indices changed')
    return {'file':str(path),'vertices':len(vertices),'bones':bones,'global_skin':global_skin,'version':data['version']}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--converter',type=Path,required=True);p.add_argument('--mesh',type=Path,action='append',required=True);p.add_argument('--global-skin',action='store_true');p.add_argument('--particles',type=Path);a=p.parse_args()
    try:
        m=load(a.converter.resolve());results=[check_mesh(m,x,a.global_skin) for x in a.mesh];particle=None
        if a.particles:
            pm=load(a.particles.resolve());source={'main':{},'textureSheetAnimation':{'bases':{'enable':True},'vector2s':{'tiles':[4,4]},'frame':{'type':1,'overTime':{'frames':[{'key':0,'value':0},{'key':1,'value':15}]}}}}
            out=pm.spec(source)
            if out['tiles']!=[4,4] or out['frameKeys']!=source['textureSheetAnimation']['frame']['overTime']['frames']:raise ValueError('Texture-sheet curve lost')
            particle={'synthetic_curve_preserved':True}
        print(json.dumps({'meshes':results,'particles':particle,'limits':'Structural checks only; no rendered pose or pixel equivalence. Parser remains project-local.'}));return 0
    except (OSError,ValueError,KeyError,AssertionError) as e:p.error(str(e))
if __name__=='__main__':raise SystemExit(main())
