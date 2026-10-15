# mcp-k8s-manager

Un MCP server per la gestione di cluster Kubernetes su AKS (Azure Kubernetes Service), utilizzabile da Claude Desktop. Offre strumenti per eseguire comandi `kubectl` e `kubectx` direttamente da un'interfaccia conversazionale.

---

## Requisiti

Assicurati di avere installato:

- Python ≥ 3.10
- kubectl
- kubectx
- Azure CLI
- Claude Desktop

---

## Installazione locale

1. Clona il repository:

```bash
git clone https://github.com/crtdaniele/mcp-k8s-manager
cd mcp-k8s-manager
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

- **run_kubectx:**

Cambia contesto Kubernetes usando kubectx.

- **run_kubectl:**

Esegue comandi kubectl. È possibile cambiare contesto prima con kubectx.

## Installazione su Claude Desktop

```bash
mcp install main.py
```

Oppure configura manualmente il file settings.json (Claude Desktop > Settings > Advanced):

```bash
{
  "mcpServers": {
    "mcp-k8s-manager": {
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "mcp",
        "run",
        "your-local-path/main.py"
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
