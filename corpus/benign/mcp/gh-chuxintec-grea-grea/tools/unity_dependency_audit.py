#!/usr/bin/env python3
"""Read-only GUID closure audit of a text-serialized Unity Assets export."""
import argparse
import collections
import hashlib
import json
from grea.host.paths import Path
import re
import sys

GUID = re.compile(r'\bguid:\s*([0-9a-fA-F]{32})\b')
META = re.compile(r'^guid:\s*([0-9a-fA-F]{32})\s*$', re.M)
TEXT = {'.prefab', '.unity', '.asset', '.mat', '.controller', '.anim', '.overridecontroller', '.playable', '.mask'}
CODE = {'.cs', '.dll'}

def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()

def within(root, rel):
    p = Path(rel)
    if p.is_absolute() or '..' in p.parts: raise ValueError('Root must be a relative path inside Assets: ' + rel)
    full = root / p
    if full.is_symlink() or root not in full.resolve().parents: raise ValueError('Unsafe root: ' + rel)
    if not full.is_file(): raise ValueError('Root file missing: ' + rel)
    return p.as_posix()

def audit(root, roots, max_bytes):
    index = collections.defaultdict(list); issues = []; meta_hashes = {}
    # Never traverse linked directories or files.
    import os
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(base)/d).is_symlink())
        for name in sorted(files):
            p = Path(base)/name
            if p.is_symlink():
                issues.append({'kind':'symlink_skipped','path':str(p.relative_to(root))}); continue
            if p.suffix != '.meta': continue
            if p.stat().st_size > max_bytes:
                issues.append({'kind':'oversize_meta','path':str(p.relative_to(root))}); continue
            raw = p.read_bytes()
            try: text = raw.decode('utf-8-sig')
            except UnicodeError:
                issues.append({'kind':'invalid_meta','path':str(p.relative_to(root))});continue
            m = META.search(text)
            if not m:
                issues.append({'kind':'missing_guid','path':str(p.relative_to(root))});continue
            asset = p.with_suffix('')
            if asset.is_symlink():
                issues.append({'kind':'symlink_skipped','path':str(asset.relative_to(root))});continue
            rel = str(asset.relative_to(root)); index[m[1].lower()].append(rel)
            meta_hashes[rel] = hashlib.sha256(raw).hexdigest()
    for g, paths in sorted(index.items()):
        if len(paths)>1: issues.append({'kind':'duplicate_guid','guid':g,'paths':paths})
    pending = list(roots); seen = set(); assets=[]; scripts=[]; external=[]; builtins=[]
    while pending:
        rel=pending.pop()
        if rel in seen: continue
        seen.add(rel); p=root/rel
        if p.is_symlink() or root not in p.resolve().parents:
            issues.append({'kind':'unsafe_dependency','path':rel});continue
        if not p.is_file():
            issues.append({'kind':'missing_asset','path':rel});continue
        row={'path':rel,'sha256':digest(p),'meta_sha256':meta_hashes.get(rel),'size':p.stat().st_size}
        if not row['meta_sha256']:issues.append({'kind':'missing_meta','path':rel})
        if p.suffix.lower() in CODE:
            scripts.append(row);continue
        assets.append(row)
        candidates=[p]
        if Path(str(p)+'.meta').is_file():candidates.append(Path(str(p)+'.meta'))
        for scan in candidates:
            if scan.suffix != '.meta' and scan.suffix.lower() not in TEXT:continue
            if scan.stat().st_size>max_bytes:
                issues.append({'kind':'oversize_unscanned','path':str(scan.relative_to(root))});continue
            try: body=scan.read_text(encoding='utf-8-sig')
            except UnicodeError:
                issues.append({'kind':'binary_unscanned','path':str(scan.relative_to(root))});continue
            if scan.suffix != '.meta' and not body.lstrip().startswith('%YAML'):
                issues.append({'kind':'non_yaml_unscanned','path':rel});continue
            for g in sorted(set(x.lower() for x in GUID.findall(body))):
                targets=index.get(g,[])
                if len(targets)==1:pending.append(targets[0])
                elif len(targets)>1:issues.append({'kind':'ambiguous_reference','from':rel,'guid':g})
                elif g.startswith('0000000000000000'):
                    builtins.append({'from':rel,'guid':g})
                else:external.append({'from':rel,'guid':g})
    return {'schema_version':1,'source':str(root),'roots':roots,'assets':sorted(assets,key=lambda x:x['path']),
            'excluded_code_review_required':sorted(scripts,key=lambda x:x['path']),
            'unresolved_references':external,'builtin_candidates':builtins,'issues':issues,
            'limits':['Text GUID references only; no binary PPtr or runtime string loads.',
                      'Code excluded for review, not automatically classified as stubs.',
                      'Built-in GUID candidates require Editor verification.',
                      'No copying, remapping or runtime/visual verification.']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--assets',type=Path,required=True,help='Source exported Assets directory')
    p.add_argument('--root',action='append',required=True,help='Relative root asset; repeatable')
    p.add_argument('--output',type=Path,required=True,help='New report outside source tree; never overwritten')
    p.add_argument('--max-text-mib',type=int,default=32)
    a=p.parse_args()
    try:
        source=a.assets.resolve(strict=True)
        if not source.is_dir() or a.max_text_mib<=0:raise ValueError('Invalid source or size limit')
        output=a.output.absolute()
        if output.is_symlink() or output.exists():raise ValueError('Output exists')
        resolved=output.resolve()
        if source==resolved or source in resolved.parents:raise ValueError('Output must be outside source')
        roots=[within(source,x) for x in a.root]
        report=audit(source,roots,a.max_text_mib*1024*1024)
        # Parent must exist: never create arbitrary directory trees implicitly.
        with output.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
        incomplete=bool(report['issues'] or report['unresolved_references'])
        print(json.dumps({'report':str(output),'assets':len(report['assets']), 'excluded_code':len(report['excluded_code_review_required']), 'unresolved':len(report['unresolved_references']),'issues':len(report['issues']),'status':'needs_review' if incomplete else 'static_scan_complete'}))
        return 1 if incomplete else 0
    except (OSError,ValueError) as e:
        print(str(e),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
