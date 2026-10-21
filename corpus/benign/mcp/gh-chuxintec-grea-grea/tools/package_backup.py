#!/usr/bin/env python3
"""Snapshot installed non-builtin UPM packages and prepare verified offline install plans."""
import argparse,hashlib,json,tarfile,tempfile,os,re
from grea.host.paths import Path
from grea.safe_paths import disjoint, relative_name

def sha(p,private_markers=()):
 h=hashlib.sha256()
 with p.open('rb') as f:
  tail=b''
  for b in iter(lambda:f.read(1048576),b''):
   data=tail+b
   if any(marker in data for marker in private_markers):raise ValueError('Package contains environment-specific paths; remove generated caches or select a clean package source before snapshot.')
   tail=data[-4096:];h.update(b)
 return h.hexdigest()
def public_member(member):
 member.uid=member.gid=0;member.uname=member.gname='';member.mtime=0
 member.pax_headers={k:v for k,v in member.pax_headers.items() if k not in {'atime','ctime','mtime','uid','gid','uname','gname'}}
 return member

def snapshot(projects,dest):
 dest=disjoint(dest,*projects)
 if dest.exists():raise ValueError('Output must be a new directory')
 # Validate every identity before creating any archives.
 for project in projects:
  lock=json.loads((project/'Packages/packages-lock.json').read_text(encoding='utf-8'))['dependencies']
  for name in lock:
   if not re.fullmatch(r'[a-z][a-z0-9._-]+',name):raise ValueError('Invalid package name')
  for base in [project/'Library/PackageCache',project/'Packages']:
   for metadata in base.glob('*/package.json'):
    pkg=json.loads(metadata.read_text(encoding='utf-8'))
    if not re.fullmatch(r'[a-z][a-z0-9._-]+',pkg['name']) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?',pkg['version']):raise ValueError('Invalid package identity')
 dest.mkdir(parents=True);(dest/'archives').mkdir();items={};inventories=[];missing=[]
 for source_index,project in enumerate(projects,1):
  private_markers=tuple(str(x).encode() for x in (project.resolve(),Path.home()) if len(str(x))>3)
  lock=json.loads((project/'Packages/packages-lock.json').read_text(encoding='utf-8'))['dependencies'];candidates={}
  for base in [project/'Library/PackageCache',project/'Packages']:
   if base.exists():
    for p in base.iterdir():
     if p.is_dir() and (p/'package.json').is_file():
      d=json.loads((p/'package.json').read_text(encoding='utf-8'));candidates[(d.get('name'),d.get('version'))]=(p,d)
  source_id='source-'+str(source_index)
  inv={'project':source_id,'packages':[]}
  for name,meta in lock.items():
   if meta.get('source')=='builtin':continue
   # git lock version is URL, resolve by package name only when unique.
   found=candidates.get((name,meta.get('version')))
   if found is None:
    options=[v for (n,_),v in candidates.items() if n==name]
    if len(options)==1:found=options[0]
   if not found:missing.append({'project':source_id,'name':name,'version':meta.get('version')});continue
   path,pkg=found;key=name+'@'+pkg['version'];inv['packages'].append(key)
   fingerprint=[]
   for f in sorted(path.rglob('*')):
    if f.is_symlink():fingerprint.append([f.relative_to(path).as_posix(),'link:'+os.readlink(f)])
    elif f.is_file():fingerprint.append([f.relative_to(path).as_posix(),sha(f,private_markers)])
   tree=hashlib.sha256(json.dumps(fingerprint).encode()).hexdigest();identity=key+'-'+tree[:12]
   if identity not in items:
    archive=dest/'archives'/relative_name(identity+'.tgz')
    if not archive.exists():
     with tempfile.NamedTemporaryFile(dir=archive.parent,delete=False) as f:tmp=Path(f.name)
     try:
      with tarfile.open(tmp,'w:gz') as tf:tf.add(path,arcname='package',recursive=True,filter=public_member)
      # Verify content bytes before publishing.
      with tarfile.open(tmp) as tf:
       for rel,digest in fingerprint:
        if digest.startswith('link:'):continue
        obj=tf.extractfile('package/'+rel);h=hashlib.sha256()
        for b in iter(lambda:obj.read(1048576),b''):h.update(b)
        if h.hexdigest()!=digest:raise ValueError('Archive mismatch '+rel)
      with tmp.open('rb') as incoming, archive.open('xb') as outgoing:
       import shutil
       shutil.copyfileobj(incoming,outgoing)
     finally:
      if tmp.exists():tmp.unlink()
    items[identity]={'id':key,'name':name,'version':pkg['version'],'archive':archive.relative_to(dest).as_posix(),'sha256':sha(archive),'tree_sha256':tree,'dependencies':pkg.get('dependencies',{}),'resolved_dependencies':{n:lock[n]['version'] for n in pkg.get('dependencies',{}) if n in lock and lock[n].get('source')!='builtin'},'source_project':source_id,'source_path':path.relative_to(project).as_posix(),'file_count':len(fingerprint)}
  inventories.append(inv)
 report={'schema_version':1,'packages':list(items.values()),'projects':inventories,'missing':missing,'boundary':'Installed source archives, not game assets. Built-in modules require matching Editor.'}
 with (dest/'catalog.json').open('x') as f:json.dump(report,f,indent=2)
 print(json.dumps({'archives':len(items),'missing':missing}));return 1 if missing else 0

def plan(backup,requested,output):
 d=json.loads((backup/'catalog.json').read_text(encoding='utf-8'));byid={};byname={}
 for x in d['packages']:byid.setdefault(x['id'],[]).append(x);byname.setdefault(x['name'],[]).append(x)
 queue=list(requested);selected={}
 while queue:
  key=queue.pop();choices=byid.get(key,[])
  if not choices:raise ValueError('Package not backed up: '+key)
  if len(choices)!=1:raise ValueError('Ambiguous package content: '+key)
  x=choices[0]
  if x['name'] in selected:
   if selected[x['name']]['id']!=key:raise ValueError('Conflicting dependency versions: '+key)
   continue
  selected[x['name']]=x
  for n,v in x.get('resolved_dependencies',x['dependencies']).items():
   if n.startswith('com.unity.modules.'):continue
   dep=n+'@'+v
   if dep in byid:queue.append(dep)
   elif len(byname.get(n,[]))==1:raise ValueError('Exact dependency '+dep+' missing; use online UPM resolve, do not guess version')
   else:raise ValueError('Dependency not backed up: '+dep)
 packages=[]
 for x in selected.values():
  p=(backup/x['archive']).resolve()
  if backup.resolve() not in p.parents or sha(p)!=x['sha256']:raise ValueError('Archive integrity failure')
  packages.append('file:'+str(p))
 output=disjoint(output,backup)
 with output.open('x') as f:json.dump({'packages':packages,'ids':[x['id'] for x in selected.values()]},f,indent=2)
 print('Prepared verified plan:',output)

def main():
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='cmd',required=True)
 a=s.add_parser('snapshot');a.add_argument('--project',type=Path,action='append',required=True);a.add_argument('--output',type=Path,required=True)
 a=s.add_parser('plan');a.add_argument('--backup',type=Path,required=True);a.add_argument('--package',action='append',required=True);a.add_argument('--output',type=Path,required=True)
 a=p.parse_args()
 try:
  if a.cmd=='snapshot':return snapshot(a.project,a.output)
  plan(a.backup,a.package,a.output);return 0
 except (OSError,ValueError,KeyError,tarfile.TarError) as e:p.error(str(e))
if __name__=='__main__':raise SystemExit(main())
