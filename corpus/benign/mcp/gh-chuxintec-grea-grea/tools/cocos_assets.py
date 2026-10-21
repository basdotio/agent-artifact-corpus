"""Bounded offline Cocos 2.4 compiled-v1 evidence reader; never a game runtime.

Implementation derives from observed serialized protocol and independently authored examples.
Only the explicitly selected adapter is accepted. References remain data, never live objects.
"""
import argparse
import base64
import copy
import hashlib
import json
import math
from grea.host.paths import Path
import re
import sys

VERSION = '0.1.0'
ADAPTERS = ('cocos-2.4-compiled-v1', 'cocos-2.4-pack-v1', 'cocos-2.4-texture-pack-v1')


class ParseError(ValueError):
    def __init__(self, code, location, message):
        super().__init__(f'{code} at {location}: {message}')
        self.code, self.location, self.message = code, location, message

    def as_dict(self):
        return dict(code=self.code, location=self.location, message=self.message)


def fail(code, location, message):
    raise ParseError(code, location, message)


def array(value, location):
    if not isinstance(value, list): fail('INVALID_SHAPE', location, 'Expected an array')
    return value


def integer(value, location):
    if type(value) is not int: fail('INVALID_SHAPE', location, 'Expected an integer, not a boolean')
    return value


def at(table, index, location):
    integer(index, location)
    if index < 0 or index >= len(table): fail('INDEX_OUT_OF_RANGE', location, 'Table index outside declared bounds')
    return table[index]


def uuid_full(value, location):
    if not isinstance(value, str): fail('INVALID_UUID', location, 'Expected a UUID string')
    if re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', value): return value.lower()
    if re.fullmatch(r'[0-9a-fA-F]{2}[A-Za-z0-9+/]{20}', value):
        raw = value[:2] + base64.b64decode(value[2:], validate=True).hex()
        return f'{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}'
    fail('INVALID_UUID', location, 'Unsupported UUID encoding')


def budget(document, max_depth=96, max_nodes=500000):
    pending=[(document,0)]; count=0
    while pending:
        value,depth=pending.pop(); count+=1
        if isinstance(value,float) and not math.isfinite(value): fail('INVALID_NUMBER','$','Non-finite numeric value')
        if isinstance(value,str):
            try: value.encode('utf-8')
            except UnicodeError: fail('INVALID_UNICODE','$','Unpaired Unicode surrogate is unsupported')
        if depth>max_depth or count>max_nodes: fail('BUDGET_EXCEEDED','$','Depth or value budget exceeded')
        if isinstance(value,list): pending.extend((x,depth+1) for x in value)
        elif isinstance(value,dict): pending.extend((x,depth+1) for pair in value.items() for x in pair)


class CompiledV1:
    def __init__(self, document):
        d=array(document,'$')
        if not d or type(d[0]) is not int or d[0]!=1: fail('UNSUPPORTED_VERSION','$[0]','Only compiled serialization header 1 is supported')
        if len(d)!=11: fail('INVALID_SHAPE','$','Compiled-v1 requires eleven sections')
        self.uuids,self.strings,self.classes,self.masks,self.values,self.types,self.refs,self.owners,self.keys,self.deps = [
            [] if type(v) is int and v==0 else array(v,f'$[{i}]') for i,v in enumerate(d[1:],1)]
        if not all(isinstance(v,str) for v in self.strings): fail('INVALID_SHAPE','$[2]','String table must contain strings')
        if len(self.owners)!=len(self.keys) or len(self.owners)!=len(self.deps): fail('INVALID_SHAPE','$[8:11]','Dependency tables have different lengths')
        self.ref_owners={}; self.dep_owners={}; self.instances=[]; self.total=0

    def class_name(self,index,loc):
        value=at(self.classes,index,loc)
        name=value[0] if isinstance(value,list) and value else value
        if not isinstance(name,str): fail('INVALID_SHAPE',loc,'Class name must be a string')
        return name

    def assign(self,owner,key,value,loc):
        if isinstance(owner,dict) and isinstance(key,str): owner[key]=value
        elif isinstance(owner,list) and type(key) is int:
            at(owner,key,loc); owner[key]=value
        else: fail('INVALID_REFERENCE',loc,'Expected object/string key or array/integer key')

    def reference_key(self,key,loc):
        if type(key) is int: return at(self.strings,key,loc) if key>=0 else ~key
        if isinstance(key,str): return key
        fail('INVALID_REFERENCE',loc,'Invalid reference key')

    def object(self,values,loc,depth):
        array(values,loc)
        if not values: fail('INVALID_SHAPE',loc,'Missing object mask')
        mask=array(at(self.masks,values[0],loc+'.mask'),loc+'.mask')
        if len(mask)<2: fail('INVALID_SHAPE',loc+'.mask','Mask lacks class or boundary')
        cls=array(at(self.classes,mask[0],loc+'.class'),loc+'.class')
        if len(cls)<3 or not isinstance(cls[0],str): fail('INVALID_SHAPE',loc+'.class','Invalid property class')
        keys=array(cls[1],loc+'.class.keys'); offset=integer(cls[2],loc+'.class.offset')
        boundary=integer(mask[-1],loc+'.mask.boundary')
        if len(values)!=len(mask)-1 or not 1<=boundary<=len(values): fail('INVALID_SHAPE',loc,'Mask and object lengths/boundary disagree')
        result={'__type__':cls[0]}; seen=set()
        for i in range(1,len(values)):
            prop=mask[i]; key=at(keys,prop,loc+f'.property[{i}]')
            if not isinstance(key,str) or key in seen or key=='__type__': fail('INVALID_SHAPE',loc,'Invalid or duplicate property key')
            seen.add(key)
            kind=0 if i<boundary else at(cls,prop+offset,loc+'.kind')
            self.field(result,key,values[i],kind,loc+'.'+key,depth+1)
        return result

    def field(self,owner,key,value,kind,loc,depth):
        if depth>96: fail('BUDGET_EXCEEDED',loc,'Decoded nesting budget exceeded')
        integer(kind,loc+'.kind')
        if kind==0 or kind==7: result=copy.deepcopy(value)
        elif kind==1:
            integer(value,loc)
            if value>=0:
                if value>=self.total: fail('INDEX_OUT_OF_RANGE',loc,'Instance reference outside declared instances')
                result={'__id__':value}
            else:
                index=(~value)*3
                if index>=max(0,len(self.refs)-1) or index in self.ref_owners: fail('INVALID_REFERENCE',loc,'Invalid or reused deferred reference')
                self.ref_owners[index]=owner; result=None
        elif kind in (2,3,9):
            result=[None]*len(array(value,loc))
            for i,v in enumerate(value): self.field(result,i,v,{2:1,3:6,9:4}[kind],f'{loc}[{i}]',depth+1)
        elif kind==4: result=self.object(value,loc,depth+1)
        elif kind in (5,8):
            array(value,loc)
            if not value: fail('INVALID_SHAPE',loc,'Inline value type lacks identity')
            result={'__value_type__':integer(value[0],loc),'values':copy.deepcopy(value[1:])}
        elif kind==6:
            at(self.deps,value,loc)
            if value in self.dep_owners: fail('INVALID_REFERENCE',loc,'Dependency slot has multiple owners')
            self.dep_owners[value]=owner; result=None
        elif kind==10:
            if len(array(value,loc))!=2: fail('INVALID_SHAPE',loc,'Custom value must contain class and payload')
            result={'__type__':self.class_name(value[0],loc),'data':copy.deepcopy(value[1])}
        elif kind==11:
            array(value,loc)
            if not value or not isinstance(value[0],dict) or (len(value)-1)%3: fail('INVALID_SHAPE',loc,'Invalid dictionary encoding')
            result=copy.deepcopy(value[0])
            for i in range(1,len(value),3): self.field(result,value[i],value[i+2],value[i+1],f'{loc}[{i}]',depth+1)
        elif kind==12:
            array(value,loc)
            if not value: fail('INVALID_SHAPE',loc,'Missing typed array values')
            result=copy.deepcopy(array(value[0],loc))
            if len(result)!=len(value)-1: fail('INVALID_SHAPE',loc,'Typed array length mismatch')
            for i,v in enumerate(list(result)): self.field(result,i,v,value[i+1],f'{loc}[{i}]',depth+1)
        else: fail('UNSUPPORTED_KIND',loc+'.kind',f'Unsupported field kind {kind}')
        self.assign(owner,key,result,loc)

    def decode(self):
        values=list(self.values); root=0
        if values and type(values[-1]) is int: root=values.pop()
        self.total=len(values)
        if not values or len(self.types)>self.total: fail('INVALID_SHAPE','$[5]','No instances or more custom types than instances')
        normal=self.total-len(self.types)
        for i,value in enumerate(values):
            loc=f'$[5][{i}]'
            if i<normal: result=self.object(value,loc,0)
            else:
                kind=integer(self.types[i-normal],loc+'.type')
                if kind>=0: result={'__type__':self.class_name(kind,loc),'data':copy.deepcopy(value)}
                else:
                    holder=[None]; self.field(holder,0,value,~kind,loc,0); result=holder[0]
            self.instances.append(result)
        root=root if root>=0 else ~root; at(self.instances,root,'$.root')
        if self.refs:
            if (len(self.refs)-1)%3: fail('INVALID_SHAPE','$[7]','Invalid reference triples')
            embedded=integer(self.refs[-1],'$[7][-1]')*3
            if embedded<0 or embedded>len(self.refs)-1: fail('INVALID_REFERENCE','$[7]','Invalid embedded reference count')
            for i in range(0,len(self.refs)-1,3):
                owner=self.ref_owners.get(i) if i<embedded else at(self.instances,self.refs[i],f'$[7][{i}]')
                target=self.refs[i+2]; at(self.instances,target,f'$[7][{i+2}]')
                self.assign(owner,self.reference_key(self.refs[i+1],f'$[7][{i+1}]'),{'__id__':target},f'$[7][{i}]')
        for i,(owner,key,uid) in enumerate(zip(self.owners,self.keys,self.deps)):
            owner=self.dep_owners.get(i) if i in self.dep_owners else at(self.instances,owner,f'$[8][{i}]')
            uid=at(self.uuids,uid,f'$[10][{i}]') if type(uid) is int else uid
            self.assign(owner,self.reference_key(key,f'$[9][{i}]'),{'__uuid__':uuid_full(uid,f'$[10][{i}]')},f'$.dependency[{i}]')
        return dict(root=root,instances=self.instances)


def decode_document(document, adapter=ADAPTERS[0], max_depth=96):
    budget(document,max_depth=max_depth)
    if adapter==ADAPTERS[0]: return CompiledV1(document).decode()
    if adapter==ADAPTERS[1]:
        array(document,'$')
        if len(document)!=6: fail('INVALID_SHAPE','$','Pack requires shared header and sections')
        sections=array(document[5],'$[5]')
        if not sections: fail('EMPTY_INPUT','$[5]','Pack contains no sections')
        return {'sections':[dict(pack_section_ordinal=i,document=CompiledV1(document[:5]+array(section,f'$[5][{i}]')).decode()) for i,section in enumerate(sections)]}
    if adapter==ADAPTERS[2]:
        if not isinstance(document,dict) or set(document)!= {'type','data'} or document['type']!='cc.Texture2D' or not isinstance(document['data'],str): fail('INVALID_SHAPE','$','Expected the explicit Texture2D pack encoding')
        if not document['data'] or any(not x for x in document['data'].split('|')): fail('EMPTY_INPUT','$.data','Empty texture section')
        return {'sections':[dict(pack_section_ordinal=i,type='cc.Texture2D',data=value) for i,value in enumerate(document['data'].split('|'))]}
    fail('UNSUPPORTED_ADAPTER','$',f'Unknown adapter {adapter}')


def safe_path(path):
    path=Path(path).absolute()
    if any(p.is_symlink() for p in (path,*path.parents)): fail('SYMLINK_PATH',str(path),'Symlink paths are not supported')
    return path


def select_import(bundle,identity,version=None):
    """Select exact configured version, or reject ambiguity. Never take glob()[0]."""
    bundle=safe_path(bundle)
    if not re.fullmatch(r'[A-Za-z0-9_-]+',identity) or version is not None and not re.fullmatch(r'[A-Za-z0-9_-]+',version): fail('INVALID_SELECTION','$.selection','Invalid import identity or version')
    folder=bundle/'import'/identity[:2]
    candidates=[folder/f'{identity}.{version}.json'] if version is not None else sorted(folder.glob(identity+'.*.json'))
    if len(candidates)!=1: fail('AMBIGUOUS_SELECTION' if candidates else 'MISSING_INPUT','$.selection','Exactly one source version is required')
    candidate=safe_path(candidates[0])
    if not candidate.is_file(): fail('MISSING_INPUT','$.selection','Configured source version does not exist')
    return candidate


def load_json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result: fail('DUPLICATE_KEY','$','Duplicate JSON object key')
            result[key]=value
        return result
    try: return json.loads(raw.decode('utf-8-sig'),object_pairs_hook=pairs,parse_constant=lambda x: fail('INVALID_JSON','$','Non-finite JSON number'))
    except ParseError: raise
    except (UnicodeError,ValueError,RecursionError) as error: fail('INVALID_JSON','$',str(error))


def export_document(source,output,adapter=ADAPTERS[0],max_bytes=32*1024*1024,max_output_bytes=64*1024*1024):
    source,output=safe_path(source),safe_path(output)
    if output.exists(): fail('OUTPUT_EXISTS',str(output),'Candidate directory must be new')
    if max_bytes<=0 or max_bytes>256*1024*1024: fail('INVALID_BUDGET','$','Input budget must be 1..256 MiB')
    with source.open('rb') as stream: raw=stream.read(max_bytes+1)
    if len(raw)>max_bytes: fail('BUDGET_EXCEEDED',str(source),'Source exceeds input byte budget')
    if not 1<=max_output_bytes<=64*1024*1024: fail('INVALID_BUDGET','$','Candidate output budget must be 1..64 MiB')
    decoded=decode_document(load_json(raw),adapter)
    payload=(json.dumps(decoded,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    if len(payload)>max_output_bytes: fail('BUDGET_EXCEEDED','$','Candidate output exceeds byte budget')
    report=dict(schema_version=1,tool='cocos_assets',implementation_version=VERSION,source_format=adapter,
                status='complete',source=dict(name=source.name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)),
                selection=dict(adapter=adapter),outputs=[dict(path='decoded.json',sha256=hashlib.sha256(payload).hexdigest())],
                errors=[],unsupported=[],scope='Explicit source only; structural evidence, not rendering or gameplay parity',
                effects=['filesystem_read','create_only_candidate'])
    output.mkdir(parents=True,exist_ok=False)
    (output/'decoded.json').write_bytes(payload)
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    return report


def export_bundle(config,asset_indices,output,pack_adapter=ADAPTERS[1],max_output_bytes=64*1024*1024):
    config,output=safe_path(config),safe_path(output)
    from grea.safe_paths import overlaps
    if overlaps(output,config.parent): fail('OUTPUT_OVERLAPS_SOURCE',str(output),'Bundle output must be outside source bundle')
    if output.exists(): fail('OUTPUT_EXISTS',str(output),'Candidate directory must be new')
    if not 1<=max_output_bytes<=64*1024*1024: fail('INVALID_BUDGET','$','Candidate output budget must be 1..64 MiB')
    if pack_adapter not in ADAPTERS[1:]: fail('UNSUPPORTED_ADAPTER','$','Select an explicit pack adapter')
    if not asset_indices or len(asset_indices)>64 or len(set(asset_indices))!=len(asset_indices): fail('INVALID_SELECTION','$','Select 1..64 distinct asset indices')
    def read(path):
        with path.open('rb') as stream: raw=stream.read(32*1024*1024+1)
        if len(raw)>32*1024*1024: fail('BUDGET_EXCEEDED',str(path),'Input exceeds 32 MiB')
        return raw
    config_raw=read(config); settings=load_json(config_raw); budget(settings)
    if not isinstance(settings,dict): fail('INVALID_SHAPE','$','Expected bundle config object')
    uuids=array(settings.get('uuids'),'$.uuids')
    canonical=[uuid_full(u,f'$.uuids[{i}]') for i,u in enumerate(uuids)]
    if len(set(canonical))!=len(canonical): fail('DUPLICATE_UUID','$.uuids','Duplicate resource identities')
    packs=settings.get('packs',{})
    if not isinstance(packs,dict): fail('INVALID_SHAPE','$.packs','Expected pack membership object')
    memberships={}
    for pack,members in packs.items():
        if not isinstance(pack,str): fail('INVALID_SHAPE','$.packs','Invalid pack identity')
        for ordinal,index in enumerate(array(members,'$.packs.'+pack)):
            at(uuids,index,'$.packs.'+pack)
            if index in memberships: fail('AMBIGUOUS_PACK','$.packs','Asset appears in multiple pack sections')
            memberships[index]=(pack,ordinal,len(members))
    versions=settings.get('versions',{})
    if not isinstance(versions,dict): fail('INVALID_SHAPE','$.versions','Expected versions object')
    imported=array(versions.get('import',[]),'$.versions.import')
    if len(imported)%2: fail('INVALID_SHAPE','$.versions.import','Version key/hash pairs are truncated')
    version_map={}
    for i in range(0,len(imported),2):
        key,value=imported[i:i+2]
        if type(key) not in (int,str) or not isinstance(value,str): fail('INVALID_SHAPE','$.versions.import','Invalid version pair')
        tagged=(type(key).__name__,key)
        if tagged in version_map: fail('AMBIGUOUS_VERSION','$.versions.import','Duplicate version identity')
        version_map[tagged]=value
    selection=[]; sources={}; decoded={}; payloads=[]; total_bytes=0; output_bytes=0
    for index in asset_indices:
        at(uuids,index,'$.selection.asset_index'); member=memberships.get(index)
        identity,ordinal,count=member if member else (canonical[index],None,None)
        version=version_map.get(('str',identity)) if member else version_map.get(('int',index),version_map.get(('str',identity)))
        path=select_import(config.parent,identity,version)
        if path not in decoded:
            raw=read(path);total_bytes+=len(raw)
            if total_bytes>64*1024*1024: fail('BUDGET_EXCEEDED','$','Combined sources exceed 64 MiB')
            decoded[path]=decode_document(load_json(raw),pack_adapter if member else ADAPTERS[0])
            sources[path]=dict(path=path.relative_to(config.parent).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
        document=decoded[path]
        if member:
            if len(document['sections'])!=count: fail('PACK_MEMBERSHIP_MISMATCH','$.packs','Config membership and source section count disagree')
            document=document['sections'][ordinal]
        selection.append(dict(asset_index=index,uuid=canonical[index],pack=identity if member else None,
                              pack_section_ordinal=ordinal,version=version,source=sources[path]['path']))
        data=(json.dumps(document,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
        output_bytes+=len(data)
        if output_bytes>max_output_bytes: fail('BUDGET_EXCEEDED','$','Combined candidate output exceeds byte budget')
        payloads.append((canonical[index]+'.json',data))
    report=dict(schema_version=1,tool='cocos_assets',implementation_version=VERSION,source_format='cocos-2.4-bundle-config-v1',status='complete',
        source=dict(name=config.name,sha256=hashlib.sha256(config_raw).hexdigest(),bytes=len(config_raw)),
        inputs=list(sources.values()),selection=dict(assets=selection,pack_adapter=pack_adapter),
        outputs=[dict(path=name,sha256=hashlib.sha256(data).hexdigest()) for name,data in payloads],errors=[],unsupported=[],
        scope='Explicit config and selected import assets only; no native payloads, source execution or Unity asset conversion',effects=['filesystem_read','create_only_candidate'])
    output.mkdir(parents=True,exist_ok=False)
    for name,data in payloads: (output/name).write_bytes(data)
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    return report


def error_report(tool,adapter,error):
    record=error.as_dict() if isinstance(error,ParseError) else dict(code='IO_ERROR',location='$',message=str(error))
    unsupported=record['code'].startswith('UNSUPPORTED')
    return dict(schema_version=1,tool=tool,implementation_version=VERSION,source_format=adapter,status='unsupported' if unsupported else 'error',
                errors=[record],unsupported=[record] if unsupported else [],scope='Input did not complete; no validation or native conversion claim',
                effects=['filesystem_read','create_only_candidate'])


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group(required=True);group.add_argument('--input',type=Path);group.add_argument('--config',type=Path)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--asset-index',type=int,action='append')
    p.add_argument('--pack-adapter',choices=ADAPTERS[1:],default=ADAPTERS[1])
    p.add_argument('--adapter',choices=ADAPTERS+('cocos-3.4.1-index-v1','cocos-3.4.1-ccon-json-v1'),default=ADAPTERS[0]);p.add_argument('--max-bytes',type=int,default=32*1024*1024);p.add_argument('--max-output-bytes',type=int,default=64*1024*1024)
    a=p.parse_args(argv)
    try:
        if a.adapter.startswith('cocos-3.4.1-'):
            from grea.tools.cocos3_evidence import export
            report=export(a.config or a.input,a.output,a.adapter,a.asset_index)
        elif a.config:
            report=export_bundle(a.config,a.asset_index,a.output,a.pack_adapter,a.max_output_bytes)
        else:
            if a.asset_index: fail('INVALID_SELECTION','$','asset-index requires config')
            report=export_document(a.input,a.output,a.adapter,a.max_bytes,a.max_output_bytes)
    except (ParseError,OSError,ValueError,TypeError,KeyError) as error:
        report=error_report('cocos_assets','cocos-2.4-bundle-config-v1' if a.config else a.adapter,error)
        print(json.dumps(report,ensure_ascii=False));return 1 if report['status']=='unsupported' else 2
    print(json.dumps(report,ensure_ascii=False));return 0

if __name__=='__main__': sys.exit(main())
