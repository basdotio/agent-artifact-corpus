#!/usr/bin/env python3
"""Validate and merge explicitly staged corpus manifests, one writer at a time."""
import argparse
import json
from pathlib import Path
import sys
from library import Library, digest, normalize_metadata, now


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library',required=True)
    parser.add_argument('--report',required=True)
    parser.add_argument('manifests',nargs='+')
    args=parser.parse_args()
    lib=Library(args.library)
    result={'started_at':now(),'indexed':[],'skipped':[],'failures':[],'source_gaps':[]}
    try:
        for filename in args.manifests:
            manifest_path=Path(filename).resolve()
            manifest=json.loads(manifest_path.read_text())
            if not isinstance(manifest.get('documents'),list):
                raise ValueError('Manifest lacks documents array: '+filename)
            result['source_gaps'].extend({'manifest':str(manifest_path),**gap} for gap in manifest.get('failures',[]))
            for entry in manifest['documents']:
                if entry.get('status')=='already_indexed':
                    result['skipped'].append(entry)
                    continue
                try:
                    source_value=entry.get('source_path') or entry.get('json_path')
                    if not source_value or not entry.get('metadata_path'):
                        raise ValueError('Staged document lacks metadata_path or source_path/json_path')
                    source=Path(source_value).resolve()
                    meta_path=Path(entry['metadata_path']).resolve()
                    if not source.is_relative_to(manifest_path.parent) or not meta_path.is_relative_to(manifest_path.parent):
                        raise ValueError('Staged source must be within manifest directory')
                    source_hash=digest(source.read_bytes())
                    if entry.get('source_sha256') and source_hash!=entry['source_sha256']:
                        raise ValueError('Staged text SHA256 mismatch')
                    if entry.get('raw_path') and entry.get('raw_sha256'):
                        if digest(Path(entry['raw_path']).read_bytes())!=entry['raw_sha256']:
                            raise ValueError('Original capture SHA256 mismatch')
                    metadata=json.loads(meta_path.read_text())
                    normalized=normalize_metadata(metadata)
                    previous=lib.db.execute('SELECT raw_sha256,metadata FROM documents WHERE id=?',(normalized['id'],)).fetchone()
                    if previous and 'accessed_at' not in metadata and previous['raw_sha256']==source_hash:
                        # Omitted capture time must not make an unchanged input look new.
                        normalized['accessed_at']=json.loads(previous['metadata']).get('accessed_at')
                    if previous and previous['raw_sha256']==source_hash and json.loads(previous['metadata'])==normalized:
                        result['skipped'].append({'id':normalized['id'],'reason':'same staged content already indexed'})
                        continue
                    record=lib.ingest(metadata,source)
                    result['indexed'].append({'id':record['document_id'],'chunks':record['chunks'],'title':metadata['title'],'manifest':str(manifest_path)})
                    if len(result['indexed']) % 25 == 0:
                        print(json.dumps({'indexed':len(result['indexed']),'last_id':record['document_id']},ensure_ascii=False),flush=True)
                except Exception as error:
                    result['failures'].append({'manifest':str(manifest_path),'entry':entry,'error':str(error)})
                    print(json.dumps({'failed':entry.get('id') or entry.get('url'),'error':str(error)},ensure_ascii=False),flush=True)
        result['finished_at']=now();result['stats']=lib.stats()
        report=Path(args.report);report.parent.mkdir(parents=True,exist_ok=True)
        report.write_text(json.dumps(result,ensure_ascii=False,indent=2))
        print(json.dumps({'indexed':len(result['indexed']),'skipped':len(result['skipped']),'failures':len(result['failures']),'source_gaps':len(result['source_gaps']),'total_documents':result['stats']['documents'],'report':str(report)},ensure_ascii=False))
        return 1 if result['failures'] else 0
    finally:
        lib.close()


if __name__=='__main__':
    sys.exit(main())
