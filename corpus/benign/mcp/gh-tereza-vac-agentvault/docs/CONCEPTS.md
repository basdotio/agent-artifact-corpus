# AgentVault — co je hybrid search, auto-reindex a MCP

## Hybrid search
Hledání skládá **dvě stopy**:
1. **Vektor** — význam (paraphráze, čeština/angličtina podle smyslu)
2. **Klíčová slova** — přesné názvy (`Filmy`, jména, URL)

Výsledky se spojí (vážený RRF). Env `HYBRID_ALPHA` (default 0.65) = váha vektorů.
Navíc lehký boost, když dotaz sedí do **title** / cesty souboru.

## Auto-reindex
Poznámky jsou Markdown na disku. Postgres drží jen **index**.
Po zápisu přes `brain_note.py` se zavolá `~/AgentVault/./av index` — přepočítá **jen změněné** soubory.
Bez reindexu by nové tipy ve vyhledávání „nebyly“.

## MCP (Model Context Protocol)
Malý lokální server (`./av serve` na `127.0.0.1:8788`), přes který AI klient volá nástroje:
- `vault_search` — hybridní hledání
- `vault_get` — celá poznámka
- `vault_neighbors` — odkazy `[[…]]`
- `vault_write` — zápis + reindex

Telegram boti u tebe MCP typicky **nepoužívají** — stačí shell `./av search`.
MCP se hodí pro Cursor / Claude Desktop / jiné MCP klienty (SSH tunnel na 8788).
