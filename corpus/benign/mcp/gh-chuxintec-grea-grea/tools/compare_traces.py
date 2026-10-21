#!/usr/bin/env python3
"""Compare ordered JSONL evidence without changing or aligning the inputs."""
import argparse
import json
import sys
from grea.host.paths import Path

def rows(path):
    with path.open(encoding='utf-8') as stream:
        for line_number, line in enumerate(stream, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except ValueError as error:
                    raise ValueError(f'{path}:{line_number}: {error}') from error

def field(row, pointer):
    if not pointer:
        return row
    value = row
    for part in pointer[1:].split('/'):
        part = part.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            value = value[int(part)]
        elif isinstance(value, dict):
            value = value[part]
        else:
            raise ValueError(f'Cannot traverse {pointer}')
    return value

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, epilog='Exit: 0 equal, 1 different, 2 invalid input. Output goes to stdout; no files are written.')
    parser.add_argument('reference', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--field', action='append', default=[], help='JSON Pointer to compare; repeatable. Omit to compare whole records.')
    args = parser.parse_args(argv)
    if any(p and not p.startswith('/') for p in args.field):
        parser.error('--field requires JSON Pointer syntax, such as /board or /rng/calls')
    try:
        left, right = list(rows(args.reference)), list(rows(args.candidate))
        for index, (a, b) in enumerate(zip(left, right)):
            for pointer in args.field or ['']:
                av, bv = field(a, pointer), field(b, pointer)
                if av != bv:
                    print(json.dumps({'equal': False, 'record': index, 'field': pointer, 'reference': av, 'candidate': bv}, ensure_ascii=False, allow_nan=False))
                    return 1
        result = {'equal': len(left) == len(right), 'referenceRecords': len(left), 'candidateRecords': len(right)}
        if not result['equal']:
            result['record'] = min(len(left), len(right))
        print(json.dumps(result))
        return 0 if result['equal'] else 1
    except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
        parser.error(str(error))

if __name__ == '__main__':
    sys.exit(main())
