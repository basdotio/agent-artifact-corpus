# Bengaluru Misinformation Layer

An agent scaffold for checking viral Bengaluru civic claims against verified primary and news sources. It uses guarded input handling, Elasticsearch hybrid retrieval with BM25 + ELSER + RRF + Jina reranking, and Bedrock/Claude for grounded verdict generation.

## What Is Included

- `app/security.py`: claim sanitizer and prompt-injection rejection.
- `app/retrieval.py`: guarded Elasticsearch hybrid query builder and live retriever.
- `app/bedrock.py`: fixed-system-prompt Bedrock verdict generator with JSON validation.
- `elastic/`: Dev Tools assets for ingest pipeline, index mapping, sample docs, and hybrid query.
- `kibana/dashboard.ndjson`: Kibana dashboard for monitoring source coverage and activity.
- `docker-compose.yml`: Local development stack with Elasticsearch and Kibana.
- `crawler.py`: Web crawler for indexing civic sources into Elasticsearch.
- `mcp_server.py`: Model Context Protocol server for tool integration.
- `.crawler.yml`: Open Crawler source rules and extraction selectors.
- `agent_builder/fact_check_tool.json`: Elastic Agent Builder-style tool contract and guardrails.

## Setup

```powershell
cd bengaluru_misinfo_layer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,live,mcp,crawler]"
Copy-Item .env.example .env
```

Fill `.env` with your Elasticsearch API key and Bedrock settings.

For offline unit tests only, `python -m pip install -e ".[dev]"` is enough.

## Local Development with Docker

```powershell
docker-compose up -d elasticsearch kibana
# Wait for services to be healthy
python -m pip install -e ".[live]"
# Run setup scripts
```

## Elastic Setup Order

Run these from Kibana Dev Tools:

1. `elastic/01_ingest_pipeline.json`
2. `elastic/02_index_and_alias.json`
3. Bulk-load `elastic/03_sample_documents.ndjson`
4. Test with `elastic/04_hybrid_query.json`

The sample corpus includes Bangalore civic announcements for transit, power, water, waste, and local traffic.

## Import Kibana Dashboard

```powershell
# From Kibana UI: Management → Saved Objects → Import
# Import kibana/dashboard.ndjson
```

Before production crawling, verify each selector in `.crawler.yml` against the current source HTML. Official civic sites often change markup without warning, the tiny goblins.

## Run A Claim Check

```powershell
bengaluru-fact-check "BMRCL is shutting Purple Line on Tuesday"
```

## Run the Crawler

```powershell
# Crawl default URLs and index to Elasticsearch
bengaluru-crawler

# Crawl specific URLs
bengaluru-crawler --urls "https://www.bmrcl.co.in/press/2025-05-07-purple-line-block" "https://bbmp.gov.in/circulars/2025-plastic-ban"

# Dry run (extract but don't index)
bengaluru-crawler --dry-run --urls "https://example.com"
```

## Run the Website

```powershell
bengaluru-web
```

Then open http://localhost:8000 in your browser.

## Run MCP Server

```powershell
bengaluru-mcp-server
```

The CLI returns:

```json
{
  "verdict": "SUPPORTED | CONTRADICTED | UNVERIFIED",
  "confidence": 0.0,
  "reasoning": "...",
  "citations": []
}
```

## Safety Model

The claim is treated as hostile input. It is normalized, capped at 500 characters, and rejected when it contains instruction-like text. The claim is never placed in the system prompt; it only appears in the user turn beside retrieved evidence. The output is parsed through a strict schema, and malformed model output falls back to `UNVERIFIED`.

## Local Validation

```powershell
pytest
```
