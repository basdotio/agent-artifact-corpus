"""Typed authoring preflight v1. No expression evaluation or inferred foreign keys."""
import argparse
import math
from grea.host.paths import Path
import sys
from grea.data_io import load, encode
from grea.safe_paths import disjoint

KINDS = {'int', 'double', 'bool', 'string'}


def scalar(value, field):
    kind = field['type']
    if kind == 'int':
        valid = type(value) is int and -2147483648 <= value <= 2147483647
    elif kind == 'double':
        valid = type(value) in (float, int) and math.isfinite(value) and (type(value) is float or abs(value) <= 2**53)
    elif kind == 'string':
        valid = type(value) is str and len(value) <= 4096
    else:
        valid = type(value) is bool
    if not valid:
        raise ValueError('Type/range mismatch for '+field['name'])
    if kind in ('int', 'double') and not field.get('min', -math.inf) <= value <= field.get('max', math.inf):
        raise ValueError('Value outside declared bounds: '+field['name'])


def validate_rows(table, rows):
    if set(table)-{'name', 'path', 'authoring', 'key', 'fields'} or not {'name','path','authoring','key','fields'} <= set(table):
        raise ValueError('Closed table contract required')
    if table['authoring'] not in ('json', 'excel_export', 'scriptableobject_export'):
        raise ValueError('Declare one authoring source; exports must be produced by that source')
    fields = table['fields']
    if not isinstance(fields, list) or not 1 <= len(fields) <= 256:
        raise ValueError('Expected 1..256 fields')
    by_name = {}
    for f in fields:
        if not isinstance(f,dict) or set(f)-{'name','type','array','optional','nullable','min','max'} or not {'name','type'} <= set(f):
            raise ValueError('Invalid field contract')
        if not isinstance(f['name'],str) or not f['name'] or f['name'] in by_name or f['type'] not in KINDS:
            raise ValueError('Duplicate field or unsupported type')
        for flag in ('array','optional','nullable'):
            if type(f.get(flag, False)) is not bool: raise ValueError('Boolean field flag required')
        for bound in ('min','max'):
            if bound in f and (f['type'] not in ('int','double') or type(f[bound]) not in (int,float) or not math.isfinite(f[bound])):
                raise ValueError('Finite numeric bounds required')
        if f.get('min',-math.inf) > f.get('max',math.inf): raise ValueError('Reversed bounds')
        by_name[f['name']] = f
    key = table['key']
    if key not in by_name or by_name[key]['type'] not in ('int','string') or any(by_name[key].get(flag,False) for flag in ('nullable','optional','array')):
        raise ValueError('Required non-null scalar int/string key required')
    if not isinstance(rows,list) or not 1 <= len(rows) <= 10000:
        raise ValueError('Expected 1..10000 rows')
    keys, states = set(), []
    for row in rows:
        if not isinstance(row,dict) or set(row)-set(by_name): raise ValueError('Unknown row field')
        state = {}
        for name, f in by_name.items():
            if name not in row:
                if not f.get('optional',False): raise ValueError('Missing required field: '+name)
                state[name] = 'missing'
                continue
            value = row[name]
            if value is None:
                if not f.get('nullable',False): raise ValueError('Unexpected null: '+name)
                state[name] = 'null'
                continue
            state[name] = 'value'
            if f.get('array',False):
                if not isinstance(value,list) or len(value)>4096: raise ValueError('Expected bounded array')
                for item in value: scalar(item,f)
            else: scalar(value,f)
        if row[key] in keys: raise ValueError('Duplicate row key')
        keys.add(row[key]); states.append(state)
    return states


def inspect(contract_path):
    path = Path(contract_path).absolute()
    contract, contract_sha = load(path)
    if not isinstance(contract,dict) or set(contract)!={'schema_version','codec','tables','references'} or contract['schema_version'] != 1 or contract['codec'] != 'typed-json-v1':
        raise ValueError('Expected closed typed-json-v1 contract')
    if not isinstance(contract['tables'],list) or not 1<=len(contract['tables'])<=128 or not isinstance(contract['references'],list) or len(contract['references'])>512:
        raise ValueError('Table/reference budget exceeded')
    tables, outputs = {}, []
    for table in contract['tables']:
        name = table['name']
        if not isinstance(name,str) or not name or name in tables: raise ValueError('One authoring source per named table required')
        relative = Path(table['path'])
        if relative.is_absolute() or '..' in relative.parts: raise ValueError('Table path must remain relative to contract')
        source = path.parent/relative
        rows, digest = load(source)
        states = validate_rows(table,rows)
        tables[name] = (table, rows)
        outputs.append(dict(name=name, source_sha256=digest, authoring=table['authoring'], rows=rows, states=states))
    checked = 0
    for ref in contract['references']:
        if not isinstance(ref,dict) or set(ref)!={'from_table','field','to_table','key','sentinels'} or not isinstance(ref['sentinels'],list):
            raise ValueError('Explicit closed reference rule required')
        source, rows = tables[ref['from_table']]; target, target_rows = tables[ref['to_table']]
        field = next((f for f in source['fields'] if f['name']==ref['field']),None)
        target_field = next((f for f in target['fields'] if f['name']==ref['key']),None)
        if not field or ref['key']!=target['key'] or field['type']!=target_field['type']: raise ValueError('Reference field/key type mismatch')
        for sentinel in ref['sentinels']: scalar(sentinel,field)
        allowed = {row[ref['key']] for row in target_rows} | set(ref['sentinels'])
        for row in rows:
            if ref['field'] not in row or row[ref['field']] is None: continue
            values = row[ref['field']] if field.get('array') else [row[ref['field']]]
            if any(v not in allowed for v in values): raise ValueError('Missing declared cross-table reference')
            checked += len(values)
    return dict(schema_version=1, tool='config_preflight', codec='typed-json-v1', status='complete',
                contract_sha256=contract_sha, tables=outputs, checked_references=checked,
                scope='Declared JSON exports and explicit references only; missing/null/value preserved; no Excel formulas, delimiter inference, RNG, game execution or Unity readback')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        report=inspect(args.contract)
        output=disjoint(args.output,args.contract.parent)
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open('xb') as stream: stream.write(encode(report))
        print(encode(dict(status='complete',output=str(output))).decode());return 0
    except (OSError,ValueError,TypeError,KeyError,OverflowError) as error:
        print(str(error),file=sys.stderr);return 2

if __name__=='__main__': sys.exit(main())
