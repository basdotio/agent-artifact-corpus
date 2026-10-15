import json
import os
from pathlib import Path

from dotenv import load_dotenv
from elasticsearch import Elasticsearch, helpers

root = Path(__file__).resolve().parent
load_dotenv(root / '.env')

es_url = os.getenv('ELASTICSEARCH_URL')
es_api_key = os.getenv('ELASTICSEARCH_API_KEY')
index_name = os.getenv('ELASTICSEARCH_INDEX', 'bengaluru-sources')

if not es_url or not es_api_key:
    raise SystemExit('Missing ELASTICSEARCH_URL or ELASTICSEARCH_API_KEY in .env')

es = Elasticsearch(es_url, api_key=es_api_key, request_timeout=30)


def parse_first_json(text: str) -> dict:
    start = text.find('{')
    if start == -1:
        raise ValueError('No JSON object found')
    depth = 0
    for i, ch in enumerate(text[start:]):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return json.loads(text[start : start + i + 1])
    raise ValueError('Unmatched braces while parsing JSON')

# Create ingest pipeline
pipeline_path = root / 'elastic' / '01_ingest_pipeline.json'
with pipeline_path.open('r', encoding='utf-8') as f:
    content = f.read().strip()
    first_newline = content.find('\n')
    body = json.loads(content[first_newline + 1 :])

es.ingest.put_pipeline(id='bengaluru-sources-pipeline', body=body)
print('Pipeline created or updated')

# Create index if missing
if not es.indices.exists(index=index_name):
    settings_path = root / 'elastic' / '02_index_and_alias.json'
    with settings_path.open('r', encoding='utf-8') as f:
        content = f.read().strip()
        body = parse_first_json(content)
    body['settings']['default_pipeline'] = 'bengaluru-sources-pipeline'
    body['settings'].pop('number_of_shards', None)
    body['settings'].pop('number_of_replicas', None)
    es.indices.create(index=index_name, body=body)
    print(f'Index created: {index_name}')
else:
    print(f'Index already exists: {index_name}')

# Bulk ingest sample docs
ndjson_path = root / 'elastic' / '03_sample_documents.ndjson'
with ndjson_path.open('r', encoding='utf-8') as f:
    lines = [line.strip() for line in f if line.strip()]

actions = []
for i in range(0, len(lines), 2):
    if i + 1 >= len(lines):
        break
    doc = json.loads(lines[i + 1])
    actions.append({'_index': index_name, '_source': doc})

if actions:
    helpers.bulk(es, actions)
    print('Sample documents indexed')
    es.indices.refresh(index=index_name)
    print('Index refreshed')
else:
    print('No sample documents found to index')
