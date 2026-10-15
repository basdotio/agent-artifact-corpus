# mcp-medium-accelerator

Questo MCP server permette a LLM come ad esempio Claude Desktop, dando in input una URL tipo "https://medium.com/tag/frontend/archive" di estrapolare tutti i link degli ultimi articoli. Creare un riassunto, anche in italiano degli articoli che interessano all'utente. Salvare il riassunto in una memoria locale da poter interpellare in qualsiasi momento.

---

## Requisiti

Assicurati di avere installato:

- Python ≥ 3.10
- Claude Desktop

---

## Installazione locale

1. Clona il repository:

```bash
git clone https://github.com/crtdaniele/mcp-medium-accelerator
cd mcp-medium-accelerator
```

2. Crea e attiva un ambiente virtuale:

```bash
python -m venv venv
source venv/bin/activate
```

3. Installa le dipendenze:

```bash
pip install -r requirements.txt
```

4. (Facoltativo) Aggiorna il file requirements.txt dopo aver aggiunto nuove librerie:

```bash
pip freeze > requirements.txt
```

## Avvio del server MCP

Per eseguire il server MCP in modalità sviluppo con hot reload:

```bash
mcp dev main.py
```

Per eseguire il server in modalità normale:

```bash
mcp run main.py
```

## Tool

Tool disponibili:

- **extract_article_links:**

Estrae i link degli articoli da un URL di archivio Medium. Restituisce una lista di link agli articoli.

- **extract_article_text:**

Estrae il contenuto di un articolo da un URL di Medium. Restituisce il contenuto dell’articolo. Chiede all’utente se desidera salvare il riassunto tramite save_summary.

- **save_summary:**

Salva un riassunto di un articolo con titolo, URL e tag. Restituisce un messaggio di stato.

- **list_summaries:**

Elenca tutti i riassunti salvati. Restituisce una lista di riassunti.

## Installazione su Claude Desktop

```bash
mcp install main.py
```

Oppure configura manualmente il file settings.json (Claude Desktop > Settings > Advanced):

```bash
{
  "mcpServers": {
    "mcp-medium-accelerator": {
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "run",
        "--with",
        "bs4",
        "--with",
        "httpx",
        "--with",
        "datetime",
        "--with",
        "tinydb",
        "--with",
        "mcp[cli]",
        "mcp",
        "run",
        "/your-local-path/main.py"
      ]
    }
  }
}
```

## Licenza

MIT License.
© 2025 Daniele Carta

# Contribuire

Pull request benvenute!

Segnala bug o richiedi funzionalità aprendo una issue.
