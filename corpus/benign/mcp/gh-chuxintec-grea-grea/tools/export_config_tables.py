#!/usr/bin/env python3
"""Export TextAssets with observed identities; optional explicit level-table checks."""
import argparse
from collections import Counter, defaultdict
import json
from grea.host.paths import Path

from grea.common import hash_file
from grea.data_io import decode, encode, sha
from grea.safe_paths import relative_name, unique_paths, disjoint, write_bytes_new

ADAPTERS = ('generic', 'level-datas-v1')


def raw_script(value):
    if isinstance(value, str):
        return value.encode('utf-8', errors='surrogateescape')
    return bytes(value)


def asset_identity(reader):
    return (getattr(getattr(reader, 'assets_file', None), 'name', None), reader.path_id)


def level_summary(tables):
    """Only the named legacy dialect; missing tables are not empty valid tables."""
    names = ('LevelConfig', 'MapConfig', 'ChapterConfig')
    missing = [name for name in names if name not in tables]
    if missing:
        return dict(adapter='level-datas-v1', status='not_applicable', missing_tables=missing)
    rows = {}
    for name in names:
        value = tables[name]
        if not isinstance(value, dict) or not isinstance(value.get('Datas'), list):
            raise ValueError('level-datas-v1 requires a Datas array: ' + name)
        if any(not isinstance(row, dict) for row in value['Datas']):
            raise ValueError('Table rows must be objects: ' + name)
        rows[name] = value['Datas']
    levels, maps, chapters = (rows[name] for name in names)
    if not levels or not maps or not chapters:
        return dict(adapter='level-datas-v1', status='not_applicable', reason='Empty required table',
                    row_counts={name: len(value) for name, value in rows.items()})
    ids = [row.get('ID') for row in levels]
    references = [row.get('MapId') for row in levels]
    map_ids = [row.get('Id') for row in maps]
    chapter_ids = []
    for row in chapters:
        if not isinstance(row.get('LevelIDs'), list):
            raise ValueError('Chapter LevelIDs must be an explicit array')
        chapter_ids.extend(row['LevelIDs'])
    if any(type(value) is not int for value in ids + references + map_ids + chapter_ids):
        raise ValueError('level-datas-v1 identity fields must be integers')
    checks = dict(
        level_ids_contiguous_1_to_count=ids == list(range(1, len(ids) + 1)),
        unique_level_map_ids=len(set(references)),
        missing_map_ids=sorted(set(references) - set(map_ids)),
        all_level_map_ids_resolved=set(references) <= set(map_ids),
        chapter_level_references=len(chapter_ids),
        unique_chapter_level_references=len(set(chapter_ids)),
        all_levels_covered_by_chapters=set(ids) <= set(chapter_ids),
        missing_chapter_level_ids=sorted(set(chapter_ids) - set(ids)),
        duplicate_map_ids=len(map_ids) != len(set(map_ids)),
    )
    passed = (checks['level_ids_contiguous_1_to_count'] and checks['all_level_map_ids_resolved']
              and checks['all_levels_covered_by_chapters'] and not checks['missing_chapter_level_ids']
              and not checks['duplicate_map_ids'])
    return dict(adapter='level-datas-v1', status='passed' if passed else 'needs_review',
                row_counts={name: len(value) for name, value in rows.items()}, cross_table_validation=checks)


def export_environment(environment, bundle, output, adapter='generic'):
    if adapter not in ADAPTERS:
        raise ValueError('Unknown configuration adapter')
    source = hash_file(bundle)
    output = disjoint(output, bundle)
    selected = [(obj, obj.read()) for obj in environment.objects if obj.type.name == 'TextAsset']
    if not selected:
        raise ValueError('No TextAssets found in the selected input')
    names = [str(asset.m_Name) for _, asset in selected]
    for name in names:
        if len(relative_name(name).parts) != 1:
            raise ValueError('TextAsset names must be portable basenames')
    unique_paths(sorted(set(names)))  # Exact duplicates are disambiguated; case/Unicode aliases are rejected.
    identities = [asset_identity(obj) for obj, _ in selected]
    if len(identities) != len(set(identities)):
        raise ValueError('Ambiguous serialized-file/pathID identity')
    containers = defaultdict(list)
    for logical_path, reference in getattr(environment, 'container', {}).items():
        reader = reference.get_obj() if hasattr(reference, 'get_obj') else reference
        containers[asset_identity(reader)].append(str(logical_path))
    duplicates = Counter(names)
    files, index, tables = {}, [], {}
    for obj, asset in selected:
        name = str(asset.m_Name)
        serialized_file, path_id = asset_identity(obj)
        suffix = '__' + sha(encode([serialized_file, path_id]))[:16] if duplicates[name] > 1 else ''
        filename = name + suffix
        raw = raw_script(asset.m_Script)
        raw_name = 'raw/' + filename + '.bytes'
        files[raw_name] = raw
        paths = sorted(set(containers[asset_identity(obj)]))
        entry = dict(name=name, serialized_file=serialized_file, path_id=path_id,
                     logical_path=paths[0] if len(paths) == 1 else None, container_paths=paths,
                     path_authority='observed_container' if paths else 'unknown',
                     bytes=len(raw), sha256=sha(raw), raw_file=raw_name, json_valid=False)
        try:
            parsed = decode(raw)
        except (UnicodeError, ValueError, RecursionError):
            pass  # Raw evidence is valid even when it is not supported JSON.
        else:
            json_name = 'json/' + filename + '.json'
            files[json_name] = raw.decode('utf-8-sig').encode('utf-8')
            entry.update(json_valid=True, json_file=json_name)
            if duplicates[name] == 1:
                tables[name] = parsed
            if isinstance(parsed, dict):
                entry['root_keys'] = list(parsed)
        index.append(entry)
    summary = (level_summary(tables) if adapter == 'level-datas-v1'
               else dict(adapter='generic', status='not_applicable', reason='No business adapter selected'))
    report = dict(schema_version=2, bundle=Path(bundle).name, bundle_sha256=source['sha256'], adapter=adapter,
                  text_asset_count=len(index), json_table_count=sum(x['json_valid'] for x in index),
                  tables=sorted(index, key=lambda item: (item['name'], str(item['serialized_file']), item['path_id'])))
    files['TABLE_INDEX.json'] = encode(report)
    files['LEVEL_TABLE_SUMMARY.json'] = encode(summary)  # Retain the old output name with explicit applicability.
    unique_paths(files)
    if hash_file(bundle)['sha256'] != source['sha256']:
        raise ValueError('Source changed while exporting')
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        write_bytes_new(path, raw)
    return report, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--adapter', choices=ADAPTERS, default='generic')
    args = parser.parse_args()
    import UnityPy  # Optional provider; generic grea does not install it implicitly.
    try:
        import contextlib
        import sys
        with contextlib.redirect_stdout(sys.stderr):
            environment = UnityPy.load(str(args.bundle))
    except (ValueError, IndexError, KeyError, NotImplementedError) as error:
        print(json.dumps(dict(status='provider_decode_failed',provider='UnityPy',provider_version=UnityPy.__version__,
                              source_sha256=hash_file(args.bundle)['sha256'],error_type=type(error).__name__,
                              scope='Provider could not decode the input; unsupported format and damaged input are not distinguished. No export or business validation occurred.')))
        return 2
    report, summary = export_environment(environment, args.bundle, args.output, args.adapter)
    print(json.dumps(dict(text_assets=report['text_asset_count'], json_tables=report['json_table_count'],
                          business_validation=summary['status'])))
    return 1 if summary['status'] == 'needs_review' else 0


if __name__ == '__main__':
    raise SystemExit(main())
