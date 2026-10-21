"""Finite Creator 3.4.1 index and CCON-JSON v1 readers; no engine execution."""
import re
from grea.host.paths import Path
from grea.data_io import load, encode, sha, read_bytes
from grea.safe_paths import disjoint
from grea.tools.cocos_assets import fail, safe_path, uuid_full, decode_document

ADAPTERS = ('cocos-3.4.1-index-v1', 'cocos-3.4.1-ccon-json-v1')


def identity(value, location):
    # Subasset suffix is an identity, never a path or a class to instantiate.
    base, separator, suffix = value.partition('@') if isinstance(value, str) else ('', '', '')
    if separator and not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', suffix):
        fail('INVALID_UUID', location, 'Invalid subasset suffix')
    return uuid_full(base, location) + (separator + suffix if separator else '')


def inspect_ccon(path):
    path = safe_path(path)
    value, digest = load(path, max_bytes=32*1024*1024, max_nodes=500000)
    if not isinstance(value, dict) or set(value) != {'version', 'document', 'chunks'}:
        fail('UNSUPPORTED_FORMAT', '$', 'Expected CCON JSON, not CCONB or a compiled pack')
    if type(value['version']) is not int or value['version'] != 1:
        fail('UNSUPPORTED_VERSION', '$.version', 'Only CCON JSON v1 is supported')
    document = value['document']
    if not isinstance(document, list) or not document:
        fail('INVALID_SHAPE', '$.document', 'Expected a nonempty object table')
    if value['chunks'] != ['.bin']:
        fail('UNSUPPORTED_CHUNKS', '$.chunks', 'Only the observed single .bin sidecar is supported')
    chunk = safe_path(path.with_suffix('.bin'))
    if not chunk.is_file():
        fail('MISSING_CHUNK', '$.chunks[0]', 'Declared sidecar is absent')
    if chunk.stat().st_size > 32*1024*1024:
        fail('BUDGET_EXCEEDED', '$.chunks[0]', 'Chunk exceeds 32 MiB')
    raw = read_bytes(chunk,32*1024*1024)
    refs, pending = [], [('$', document)]
    while pending:
        location, node = pending.pop()
        if isinstance(node, dict):
            if '__id__' in node:
                index = node['__id__']
                if set(node) != {'__id__'} or type(index) is not int or not 0 <= index < len(document):
                    fail('INDEX_OUT_OF_RANGE', location, 'Object table reference is invalid')
            if node.get('__type__') == 'TypedArrayRef':
                # Uint8Array is byte-oriented and verified against actual 3.4.1 input.
                if set(node) != {'__type__', 'ctor', 'offset', 'length'} or node['ctor'] != 'Uint8Array':
                    fail('UNSUPPORTED_TYPED_ARRAY', location, 'Only Uint8Array byte references are supported')
                offset, length = node['offset'], node['length']
                if type(offset) is not int or type(length) is not int or min(offset, length) < 0 or offset+length > len(raw):
                    fail('INDEX_OUT_OF_RANGE', location, 'Typed array exceeds its chunk')
                refs.append(dict(location=location, offset=offset, length=length, sha256=sha(raw[offset:offset+length])))
            pending.extend((location+'.'+k, v) for k, v in node.items())
        elif isinstance(node, list):
            pending.extend((f'{location}[{i}]', v) for i, v in enumerate(node))
    return dict(source_sha256=digest, chunk=dict(path=chunk.name, bytes=len(raw), sha256=sha(raw)),
                references=refs, document=document, interpretation='opaque_serialized_data')


def inspect_index(path, indices):
    path = safe_path(path)
    config, digest = load(path, max_bytes=32*1024*1024, max_nodes=500000)
    required = {'importBase', 'nativeBase', 'extensionMap', 'types', 'uuids', 'packs', 'versions'}
    if not isinstance(config, dict) or not required <= set(config) or config['importBase'] != 'import' or config['nativeBase'] != 'native':
        fail('UNSUPPORTED_FORMAT', '$', 'Expected the selected Creator 3.4.1 index layout')
    if not isinstance(config['uuids'], list) or not isinstance(config['packs'], dict):
        fail('INVALID_SHAPE', '$', 'UUID list and pack mapping required')
    # Creator indices can also contain short pack IDs. They are not asset UUIDs.
    packs = config['packs']
    ids = [u if u in packs else identity(u, '$.uuids') for u in config['uuids']]
    if len(ids) != len(set(ids)):
        fail('DUPLICATE_UUID', '$.uuids', 'Duplicate identity')
    if not indices or len(indices)>64 or len(indices)!=len(set(indices)):
        fail('INVALID_SELECTION', '$', 'Select 1..64 distinct indices')
    membership = {}
    for pack, members in packs.items():
        if not re.fullmatch(r'[A-Za-z0-9_-]+', pack) or not isinstance(members, list):
            fail('INVALID_SHAPE', '$.packs', 'Invalid pack mapping')
        for ordinal, raw_index in enumerate(members):
            if type(raw_index) is int:
                index = raw_index
            elif isinstance(raw_index, str) and re.fullmatch(r'0|[1-9][0-9]*', raw_index):
                index = int(raw_index)
            else:
                fail('INVALID_SHAPE', '$.packs', 'Expected canonical decimal index')
            if not 0 <= index < len(ids) or index in membership:
                fail('AMBIGUOUS_PACK', '$.packs', 'Out-of-range or multiply packed identity')
            membership[index] = (pack, ordinal, len(members))
    versions = {}
    for kind in ('import', 'native'):
        pairs = config['versions'].get(kind, [])
        if not isinstance(pairs, list) or len(pairs)%2:
            fail('INVALID_SHAPE', '$.versions', 'Expected index/version pairs')
        target = versions[kind] = {}
        for index, version in zip(pairs[::2], pairs[1::2]):
            if type(index) is not int or not 0 <= index < len(ids) or index in target or not isinstance(version, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', version):
                fail('INVALID_VERSION', '$.versions', 'Invalid or duplicate version index')
            target[index] = version
    selected = []
    for index in indices:
        if type(index) is not int or not 0 <= index < len(ids) or ids[index] in packs:
            fail('INVALID_SELECTION', '$.selection', 'Select an asset, not a pack ID')
        member = membership.get(index)
        source_id = member[0] if member else ids[index]
        source_index = ids.index(source_id) if member else index
        version = versions['import'].get(source_index)
        if version is None:
            fail('MISSING_VERSION', '$.versions.import', 'An exact configured import version is required')
        source = safe_path(path.parent/'import'/source_id[:2]/f'{source_id}.{version}.json')
        if member:
            document, source_sha = load(source, max_bytes=32*1024*1024, max_nodes=500000)
            decoded = decode_document(document, 'cocos-2.4-pack-v1')
            if len(decoded['sections']) != member[2]:
                fail('PACK_MEMBERSHIP_MISMATCH', '$.packs', 'Section count differs from config')
            content = decoded['sections'][member[1]]
            chunks = []
        else:
            document, source_sha = load(source, max_bytes=32*1024*1024, max_nodes=500000)
            if isinstance(document, dict) and 'chunks' in document:
                content = inspect_ccon(source)
                chunks = [content['chunk']]
            else:
                content = decode_document(document, 'cocos-2.4-compiled-v1')
                chunks = []
        selected.append(dict(asset_index=index, identity=ids[index], pack=member[0] if member else None,
                             pack_section_ordinal=member[1] if member else None,
                             source=source.relative_to(path.parent).as_posix(), source_sha256=source_sha,
                             native_version=versions['native'].get(index), native_payload_checked=False,
                             chunks=chunks, content=content))
    return dict(source_sha256=digest, engine_version='3.4.1', engine_version_authority='caller_selected_adapter', assets=selected)


def export(source, output, adapter, indices=None):
    source, output = safe_path(source), safe_path(output)
    disjoint(output, source.parent)
    if output.exists():
        fail('OUTPUT_EXISTS', str(output), 'Create-only candidate required')
    result = inspect_index(source, indices) if adapter == ADAPTERS[0] else inspect_ccon(source)
    payload = encode(result)
    if len(payload)>64*1024*1024:
        fail('BUDGET_EXCEEDED', '$', 'Output exceeds 64 MiB')
    report = dict(schema_version=1, tool='cocos_assets', implementation_version='0.2.0', source_format=adapter,
                  status='complete', source=dict(name=source.name, sha256=result['source_sha256']), selection=dict(adapter=adapter,asset_indices=indices or []),
                  outputs=[dict(path='decoded.json', sha256=sha(payload))], errors=[], unsupported=[],
                  scope='Selected structural identities and chunk ranges only; no native payload, curve codec, engine execution or rendering proof',
                  effects=['filesystem_read', 'create_only_candidate'])
    output.mkdir(parents=True)
    (output/'decoded.json').write_bytes(payload)
    (output/'report.json').write_bytes(encode(report))
    return report
