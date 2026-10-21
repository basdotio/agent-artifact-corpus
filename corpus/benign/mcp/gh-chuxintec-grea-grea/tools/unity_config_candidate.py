"""Closed, scalar typed configuration candidates. No game-specific dialect inference."""
import argparse
import hashlib
import json
from grea.host.paths import Path
import re
import sys
from grea.safe_paths import disjoint
from grea.data_io import load, encode, sha

VERSION = '0.1.0'
from grea.authoring_output import identifier, write_candidate


def generate(schema_path,input_path,output):
    schema,schema_sha=load(schema_path);rows,source_sha=load(input_path)
    from grea.authoring_contracts import validate
    validate('unity-config-authoring.schema.json',schema)
    if not isinstance(schema,dict) or set(schema)!={'schema_version','namespace','name','key','fields'} or type(schema['schema_version']) is not int or schema['schema_version']!=1:
        raise ValueError('Expected closed configuration schema v1')
    name=identifier(schema['name']); ns=schema['namespace']
    if not isinstance(ns,str) or len(ns)>200: raise ValueError('Invalid namespace')
    for part in ns.split('.'): identifier(part)
    fields=schema['fields']; key=schema['key']
    if not isinstance(fields,list) or not 1<=len(fields)<=64: raise ValueError('Expected 1..64 fields')
    names=[]
    for field in fields:
        if not isinstance(field,dict) or set(field)-{'name','type','nullable','min','max'} or not {'name','type'}<=set(field): raise ValueError('Invalid field contract')
        names.append(identifier(field['name']))
        if field['name'].startswith('__grea_'): raise ValueError('Reserved generated field prefix')
        if field['type'] not in ('int','string','bool') or type(field.get('nullable',False)) is not bool: raise ValueError('Unsupported field type')
        if field.get('nullable') and field['type']!='string': raise ValueError('Only string nullability is supported')
        for bound in ('min','max'):
            if bound in field and (field['type']!='int' or type(field[bound]) is not int or not -2147483648<=field[bound]<=2147483647): raise ValueError('Integer bounds required')
        if field.get('min',-2147483648)>field.get('max',2147483647): raise ValueError('Reversed bounds')
    if name+'Row' in names: raise ValueError('Field conflicts with generated row type')
    if len(set(names))!=len(names) or key not in names: raise ValueError('Duplicate fields or missing key')
    key_field=fields[names.index(key)]
    if key_field['type'] not in ('int','string') or key_field.get('nullable'): raise ValueError('Non-null int/string key required')
    if not isinstance(rows,list) or not 1<=len(rows)<=10000: raise ValueError('Expected 1..10000 rows')
    keys=set()
    for row in rows:
        if not isinstance(row,dict) or set(row)!=set(names): raise ValueError('Missing or extra field; missing is not null')
        for field in fields:
            value=row[field['name']]; kind=field['type']
            if value is None and field.get('nullable'): continue
            if type(value) is not {'int':int,'string':str,'bool':bool}[kind]: raise ValueError('Field type mismatch')
            if kind=='int' and not field.get('min',-2147483648)<=value<=field.get('max',2147483647): raise ValueError('Out-of-range integer')
            if kind=='string' and len(value)>4096: raise ValueError('String budget exceeded')
        if row[key] in keys: raise ValueError('Duplicate row key')
        keys.add(row[key])
    # Authoring is read by the generated Editor-only importer, never by a Player.
    declarations='\n'.join(('        [SerializeField] string __grea_'+f['name']+'_value; [SerializeField] bool __grea_'+f['name']+'_hasValue;\n        public string '+f['name']+' => __grea_'+f['name']+'_hasValue ? __grea_'+f['name']+'_value : null;') if f.get('nullable') else ('        public '+f['type']+' '+f['name']+';') for f in fields)
    authoring_rows=[]
    for row in rows:
        converted={}
        for f in fields:
            value=row[f['name']]
            if f.get('nullable'):
                converted['__grea_'+f['name']+'_value']='' if value is None else value
                converted['__grea_'+f['name']+'_hasValue']=value is not None
            else:converted[f['name']]=value
        authoring_rows.append(converted)
    runtime=f'''using System; using UnityEngine;
namespace {ns} {{
    [Serializable] public sealed class {name}Row {{
{declarations}
    }}
    public sealed class {name}Table : ScriptableObject {{ public {name}Row[] rows; }}
}}
'''
    editor=f'''using System; using System.IO; using UnityEditor; using UnityEngine;
namespace {ns}.Editor {{ public static class {name}Import {{
    [Serializable] sealed class Document {{ public {name}Row[] rows; }}
    public static void Run() {{
        var args=Environment.GetCommandLineArgs();
        int a=Array.IndexOf(args,"-greaAuthoring"), b=Array.IndexOf(args,"-greaConfigAsset");
        if(a<0 || b<0 || a+1>=args.Length || b+1>=args.Length) throw new ArgumentException("Explicit authoring and new asset path required");
        Import(args[a+1],args[b+1]);
    }}
    public static void Import(string authoring,string path) {{
        if(!path.StartsWith("Assets/",StringComparison.Ordinal) || path.Contains("..") || path.Contains("\\\\") || !path.EndsWith(".asset") || File.Exists(path) || AssetDatabase.LoadMainAssetAtPath(path)) throw new IOException("New Assets asset required; no overwrite");
        var raw=File.ReadAllBytes(authoring);
        using(var hash=System.Security.Cryptography.SHA256.Create()) if(BitConverter.ToString(hash.ComputeHash(raw)).Replace("-", "").ToLowerInvariant()!="{sha(encode(dict(rows=authoring_rows)))}") throw new IOException("Authoring candidate identity changed; regenerate and review");
        var document=JsonUtility.FromJson<Document>(System.Text.Encoding.UTF8.GetString(raw));
        if(document.rows==null || document.rows.Length==0) throw new ArgumentException("Empty candidate");
        var table=ScriptableObject.CreateInstance<{name}Table>(); table.rows=document.rows;
        AssetDatabase.CreateAsset(table,path); AssetDatabase.SaveAssets();
        var actual=AssetDatabase.LoadAssetAtPath<{name}Table>(path);
        if(JsonUtility.ToJson(actual)!=JsonUtility.ToJson(table)) throw new InvalidOperationException("Readback differs");
        Debug.Log("GREA_TYPED_CONFIG_READBACK "+path+" rows="+actual.rows.Length);
    }}
}} }}
'''
    files={name+'Table.cs':runtime.encode(), 'Editor/'+name+'Import.cs':editor.encode(), 'authoring.json':encode(dict(rows=authoring_rows)), 'source-rows.json':encode(rows)}
    return write_candidate(output,files,(schema_path,input_path),dict(tool='unity_config_candidate',schema_sha256=schema_sha,input_sha256=source_sha))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schema',required=True,type=Path);p.add_argument('--input',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    try: print(json.dumps(generate(a.schema,a.input,a.output)));return 0
    except (OSError,ValueError,TypeError,KeyError,RecursionError) as error: print(str(error),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
