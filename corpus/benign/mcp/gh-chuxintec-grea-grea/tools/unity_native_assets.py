"""Finite author-declared Sprite/Transform clip preparation; never infer source-engine semantics."""
import argparse
import io
import json
import math
from grea.host.paths import Path
import sys
from PIL import Image
from grea.safe_paths import relative_name,unique_paths
from grea.data_io import load,encode,sha
from grea.authoring_output import identifier,write_candidate


def closed(value,fields):
    if not isinstance(value,dict) or set(value)!=set(fields.split()):raise ValueError('Unsupported or missing recipe fields')


def numbers(values,count,integer=False):
    if not isinstance(values,list) or len(values)!=count or any(type(x) not in ((int,) if integer else (int,float)) or not math.isfinite(x) or abs(x)>100000 for x in values):raise ValueError('Invalid bounded numeric vector')


def prepare(recipe_path,output):
    recipe,recipe_sha=load(recipe_path)
    from grea.authoring_contracts import validate
    validate('unity-native-assets.schema.json',recipe)
    closed(recipe,'schema_version sprites targets clips')
    if type(recipe['schema_version']) is not int or recipe['schema_version']!=1 or any(not isinstance(recipe[x],list) or len(recipe[x])>64 for x in ('sprites','targets','clips')):raise ValueError('Unsupported recipe or budget')
    if not recipe['sprites'] and not recipe['clips']:raise ValueError('Empty recipe')
    parent=Path(recipe_path).resolve().parent; files={};sources=[recipe_path];sprites=[];inputs={};names=[];total_pixels=0;total_input=0
    for sprite in recipe['sprites']:
        closed(sprite,'name image rect rotated_cw original_size offset pivot border pixels_per_unit'); name=identifier(sprite['name']);names.append(name+'.png')
        rel=relative_name(sprite['image']);path=parent/rel
        if any(p.is_symlink() for p in (path,*path.parents)) or path.stat().st_size>32*1024*1024:raise ValueError('Image input budget or link')
        raw=path.read_bytes();sources.append(path);inputs[rel.as_posix()]=sha(raw);total_input+=len(raw)
        if total_input>64*1024*1024:raise ValueError('Combined image input budget')
        numbers(sprite['rect'],4,True);numbers(sprite['original_size'],2,True);numbers(sprite['offset'],2,True);numbers(sprite['pivot'],2);numbers(sprite['border'],4,True)
        if type(sprite['rotated_cw']) is not bool:raise ValueError('Explicit rotation bool required')
        ppu=sprite['pixels_per_unit']
        if type(ppu) not in (int,float) or not math.isfinite(ppu) or not 0<ppu<=10000:raise ValueError('Invalid pixels per unit')
        x,y,w,h=sprite['rect'];ow,oh=sprite['original_size'];ox,oy=sprite['offset'];left,bottom,right,top=sprite['border']
        if min(x,y,ox,oy,left,bottom,right,top)<0 or min(w,h,ow,oh)<=0 or max(ow,oh)>4096 or left+right>ow or bottom+top>oh or any(not 0<=v<=1 for v in sprite['pivot']):raise ValueError('Invalid Sprite geometry')
        total_pixels+=ow*oh
        if total_pixels>32*1024*1024:raise ValueError('Combined pixel budget')
        with Image.open(io.BytesIO(raw)) as image:
            if image.width*image.height>16777216 or x+w>image.width or y+h>image.height:raise ValueError('Image geometry budget exceeded')
            crop=image.convert('RGBA').crop((x,y,x+w,y+h))
            if sprite['rotated_cw']:crop=crop.transpose(Image.Transpose.ROTATE_90)
            if ox+crop.width>ow or oy+crop.height>oh:raise ValueError('Trimmed image outside original size')
            canvas=Image.new('RGBA',(ow,oh));canvas.paste(crop,(ox,oy));stream=io.BytesIO();canvas.save(stream,format='PNG');files[name+'.png']=stream.getvalue()
        if sum(len(v) for v in files.values())>64*1024*1024:raise ValueError('Combined PNG output budget')
        sprites.append(dict(name=name,png_sha256=sha(files[name+'.png']),pivot=sprite['pivot'],border=sprite['border'],pixels_per_unit=ppu))
    unique_paths(names)
    target_names=[]
    for target in recipe['targets']:
        closed(target,'path scale');rel=relative_name(target['path']);target_names.append(rel.as_posix());numbers(target['scale'],3)
        for part in rel.parts:identifier(part)
        if len(rel.parts)>8 or any(not v for v in target['scale']):raise ValueError('Target scale/path unsupported')
    if len(set(target_names))!=len(target_names):raise ValueError('Duplicate target path')
    clips=[];clip_names=[];total_keys=0
    for clip in recipe['clips']:
        closed(clip,'name duration loop curves events');identifier(clip['name']);clip_names.append(clip['name']+'.anim')
        if type(clip['duration']) not in (int,float) or not math.isfinite(clip['duration']) or not 0<clip['duration']<=600 or type(clip['loop']) is not bool:raise ValueError('Invalid clip duration/loop')
        if not isinstance(clip['curves'],list) or not 1<=len(clip['curves'])<=128 or not isinstance(clip['events'],list) or len(clip['events'])>128:raise ValueError('Curve/event budget')
        bindings=set();curves=[]
        for curve in clip['curves']:
            closed(curve,'target property keys');binding=(curve['target'],curve['property'])
            if binding in bindings or curve['target'] not in target_names or curve['property'] not in ['m_Local'+kind+'.'+axis for kind in ('Position','Scale') for axis in ('x','y','z')]:raise ValueError('Missing/duplicate target binding or unsupported property')
            bindings.add(binding)
            keys=curve['keys']
            if not isinstance(keys,list) or not 2<=len(keys)<=10000:raise ValueError('Key budget')
            for key in keys:numbers(key,2)
            total_keys+=len(keys)
            if total_keys>20000 or keys[0][0]!=0 or keys[-1][0]!=clip['duration'] or any(a[0]>=b[0] for a,b in zip(keys,keys[1:])):raise ValueError('Strictly increasing keys must cover exactly [0,duration]')
            curves.append(dict(target=curve['target'],property=curve['property'],keys=[dict(time=k[0],value=k[1]) for k in keys]))
        for event in clip['events']:
            closed(event,'time function')
            if type(event['time']) not in (int,float) or not math.isfinite(event['time']) or not 0<=event['time']<=clip['duration'] or event['function']!='Pulse':raise ValueError('Only explicitly contracted Pulse event is supported')
        clips.append(dict(clip,curves=curves))
    unique_paths(clip_names)
    files['native-request.json']=encode(dict(schema_version=1,recipe_sha256=recipe_sha,sprites=sprites,targets=recipe['targets'],clips=clips))
    return write_candidate(output,files,sources,dict(tool='unity_native_assets',recipe_sha256=recipe_sha,image_inputs=inputs,coordinate_contract='rect/offset top-left pixels; rotated_cw undone CCW; original canvas reconstructed; pivot bottom-left normalized; border left,bottom,right,top; curves absolute local Transform units, linear interpolation'))


def spine_closure(skeleton,atlas,runtime_line):
    data,skeleton_sha=load(skeleton);version=data.get('skeleton',{}).get('spine')
    if not isinstance(version,str) or '.'.join(version.split('.')[:2])!=runtime_line:raise ValueError('Skeleton/runtime major.minor mismatch')
    atlas=Path(atlas).absolute()
    if any(p.is_symlink() for p in (atlas,*atlas.parents)) or atlas.stat().st_size>8*1024*1024:raise ValueError('Atlas budget/link')
    text=atlas.read_text(encoding='utf-8');pages=[];previous_blank=True
    # Finite text-atlas dialect: page header starts file, or a blank-delimited section, followed by size/format/filter/pma.
    lines=text.splitlines()
    for i,line in enumerate(lines):
        if line and not line[0].isspace() and ':' not in line and previous_blank:
            nextline=lines[i+1].strip() if i+1<len(lines) else ''
            if not nextline.startswith(('size:','format:','filter:','pma:')):raise ValueError('Unsupported atlas page header')
            rel=relative_name(line)
            if len(rel.parts)!=1:raise ValueError('Atlas page must be a portable basename')
            pages.append(line)
        previous_blank=not line.strip()
    if not pages or len(pages)>64:raise ValueError('Missing pages or page budget')
    unique_paths(pages);missing=[];hashes={}
    for page in pages:
        path=atlas.parent/page
        if path.is_symlink():raise ValueError('Linked atlas image')
        if not path.is_file():missing.append(page);continue
        if path.stat().st_size>32*1024*1024:raise ValueError('Page byte budget')
        hashes[page]=sha(path.read_bytes())
    return dict(schema_version=1,status='missing_pages' if missing else 'closure_observed',skeleton_version=version,runtime_line=runtime_line,skeleton_sha256=skeleton_sha,atlas_sha256=sha(atlas.read_bytes()),pages=pages,page_hashes=hashes,missing_pages=missing,runtime_import='not_run',license='not_verified',limits=['Finite text-atlas closure only; matching version does not establish runtime license, region correctness, or native import.'])


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    gen=sub.add_parser('prepare');gen.add_argument('--recipe',required=True,type=Path);gen.add_argument('--output',required=True,type=Path)
    spine=sub.add_parser('spine-check');spine.add_argument('--skeleton',required=True,type=Path);spine.add_argument('--atlas',required=True,type=Path);spine.add_argument('--runtime-line',required=True)
    a=p.parse_args()
    try:
        r=prepare(a.recipe,a.output) if a.command=='prepare' else spine_closure(a.skeleton,a.atlas,a.runtime_line);print(json.dumps(r));return 1 if r['status']=='missing_pages' else 0
    except (OSError,ValueError,TypeError,KeyError,RecursionError) as error:print(str(error),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
