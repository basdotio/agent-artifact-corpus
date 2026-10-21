# Audit Report — fattureincloud-mcp v1.8.0

> **Generato:** 2026-05-10
> **Branch:** `main` (HEAD `02834af` al momento dell'audit)
> **Modalità:** sola lettura. Nessuna modifica al codice.

Stato attuale del repository, lista dei tool esposti, copertura test, inventario dipendenze. Fonte unica di verità per la pianificazione di v1.9.0.

---

## TL;DR

- Repo a **v1.8.0** (PyPI + codice).
- README e codice espongono entrambi 20 tool con nomi allineati (nessun drift documentale).
- Cache locale: assente.
- Cost/revenue centers: non esposti.
- Test: nessuna directory `tests/`, copertura 0%.
- Tool annotations MCP (`readOnlyHint`/`destructiveHint`/...): assenti.
- Architettura: monolitica in `server.py` (1182 righe), SDK MCP raw (non FastMCP).
- Nessun git tag in repo. PyPI ha pubblicato 5 versioni storiche (1.1.0, 1.2.0, 1.3.0, 1.6.4, 1.8.0); altre voci di CHANGELOG non sono mai arrivate al registry.
- Bug noto duplicate-fattura: nessuna traccia nel codice (no TODO/FIXME, no issue GitHub).

---

## 1. Versione PyPI e tag git

| Campo | Valore |
|---|---|
| Versione PyPI corrente | **1.8.0** |
| Versione `pyproject.toml` | **1.8.0** |
| Versione header `server.py` | **1.8.0** |
| Tag git nel repo | **nessuno** |
| Versioni storiche su PyPI | `1.1.0`, `1.2.0`, `1.3.0`, `1.6.4`, `1.8.0` |
| Default branch | `main` |
| Ultimo commit al momento dell'audit | `02834af` ("v1.8.0: rimuovi mark_payment_paid/unpaid/list_payment_accounts, aggiungi convert_proforma, get_pdf_url, create/update_client") |
| Last push | 2026-02-20 |
| Stars / forks / watchers | 10 / 6 / 10 |
| Contributor unico | `aringad` |

**Note:**

1. **Nessun git tag.** Le versioni sono tracciate solo nei messaggi di commit e nel CHANGELOG.
2. **Drift PyPI vs CHANGELOG.** v1.4.0, v1.5.0, v1.6.0–v1.6.3, v1.7.0–v1.7.2 sono presenti nel CHANGELOG/commit ma non pubblicati su PyPI. Solo 1.6.4 e 1.8.0 hanno superato il salto.
3. **CHANGELOG.md non riporta v1.7.0–v1.7.2.** Quei tre commit esistono in git log ma il CHANGELOG passa direttamente da v1.6.4 a v1.8.0; la linea v1.7 introduceva `mark_payment_*` poi rimossa in v1.8.0.

---

## 2. CHANGELOG da v1.3 a v1.8

Estrazione testuale dal CHANGELOG.md attuale (più cosa il git log aggiunge per la finestra v1.7 mancante).

### v1.3.0 (PyPI)
- FIX: `create_invoice` include `ei_code` dall'anagrafica
- FIX: `duplicate_invoice` aggiorna `ei_code`
- NEW: `check_numeration`

### v1.4.0 (non pubblicato su PyPI)
- NEW: `list_invoices` accetta parametro `type`

### v1.5.0 (non pubblicato su PyPI)
- NEW: `create_credit_note` (NDC; importi positivi in input, negativi automatici; `source_invoice_id` opzionale)
- NEW: `create_proforma` (proforma, non inviabile a SDI)
- CHANGE: `list_invoices` accetta parametro `type`: `invoice` (default), `credit_note`, `proforma`

### v1.6.0 (non pubblicato su PyPI)
- NEW: `update_document` (modifica parziale di qualsiasi documento bozza: data, oggetto, righe, giorni pagamento)

### v1.6.1 / v1.6.2 / v1.6.3 (non pubblicati su PyPI)
- Tre tentativi iterativi di FIX per NDC (abs su payment, payment negativo, senza payments_list); convergono in v1.6.4

### v1.6.4 (PyPI)
- FIX: `create_credit_note` — prezzi e payment positivi (FIC inverte internamente per `type=credit_note`)
- FIX: `update_document` — stessa logica per NDC

### v1.7.0 — v1.7.2 (solo git log, non in CHANGELOG, non su PyPI)
Da git log:
- v1.7.0: aggiunti `mark_payment_paid`, `mark_payment_unpaid`, `convert_proforma`, `get_pdf_url`, `create/update_client`, `get_situation` migliorato
- v1.7.1: fix `mark_payment_paid` con `payment_account` obbligatorio, aggiunto `list_payment_accounts`
- v1.7.2: rimossa `PaymentAccountsApi` (non nel SDK), uso REST diretto per conti

### v1.8.0 (PyPI corrente)
- NEW: `convert_proforma_to_invoice` (elimina proforma originale di default; `keep_proforma=True` per mantenerla)
- NEW: `get_pdf_url` (URL PDF + link web)
- NEW: `create_client`
- NEW: `update_client`
- FIX: `get_situation` ora sottrae le NDC dal fatturato (`fatturato_netto = fatture - NDC`) e supporta filtro per cliente
- REMOVED: `mark_payment_paid`, `mark_payment_unpaid`, `list_payment_accounts` — l'API FIC richiede un conto di saldo obbligatorio non recuperabile in modo affidabile via SDK

**Note:**
- Chi fa `pip install fattureincloud-mcp` ottiene 1.8.0 con tutto lo scope corretto.
- Edge case scivolosi su NDC e payment accounts (tre minor di tentativi NDC + linea v1.7 abortita) confermano la sensibilità di queste aree dell'API FIC.

---

## 3. Tool esposti oggi (20 totali)

Estratto da `server.py` `@app.list_tools()` (righe 176–468). Ogni `Tool()` ha `name`, `description`, `inputSchema`. Nessuno ha `annotations`.

| # | Nome tool | Read-only? | Mutativo? | Descrizione | Annotations attuali |
|---|---|---|---|---|---|
| 1 | `list_invoices` | ✓ | | Lista documenti emessi (anno/mese, type=invoice/credit_note/proforma) | nessuna |
| 2 | `get_invoice` | ✓ | | Dettaglio documento per ID | nessuna |
| 3 | `get_pdf_url` | ✓ | | URL PDF e link web | nessuna |
| 4 | `list_clients` | ✓ | | Lista clienti (filtro opzionale) | nessuna |
| 5 | `get_company_info` | ✓ | | Info azienda collegata | nessuna |
| 6 | `create_client` | | ✓ | Crea cliente | nessuna |
| 7 | `update_client` | | ✓ | Aggiorna cliente | nessuna |
| 8 | `create_invoice` | | ✓ | Crea fattura (bozza) | nessuna |
| 9 | `create_credit_note` | | ✓ | Crea NDC (bozza) | nessuna |
| 10 | `create_proforma` | | ✓ | Crea proforma (bozza) | nessuna |
| 11 | `convert_proforma_to_invoice` | | ✓ | Converte proforma → fattura (elimina sorgente di default) | nessuna |
| 12 | `update_document` | | ✓ | Modifica parziale documento bozza | nessuna |
| 13 | `duplicate_invoice` | | ✓ | Duplica fattura con nuova data | nessuna |
| 14 | `delete_invoice` | | ✓ (distruttivo) | Elimina documento bozza | nessuna |
| 15 | `send_to_sdi` | | ✓ (irreversibile) | Invia documento a SDI | nessuna |
| 16 | `get_invoice_status` | ✓ | | Stato e-invoice/SDI | nessuna |
| 17 | `send_email` | | ✓ (effetto esterno) | Invia copia cortesia via email | nessuna |
| 18 | `list_received_documents` | ✓ | | Lista fatture passive | nessuna |
| 19 | `get_situation` | ✓ | | Dashboard finanziaria (fatturato netto, incassato, costi, margine; filtro cliente) | nessuna |
| 20 | `check_numeration` | ✓ | | Verifica continuità numerica fatture | nessuna |

**Conteggio:** 11 read-only, 9 mutativi (1 distruttivo `delete_invoice`, 1 irreversibile `send_to_sdi`, 1 con effetti esterni email `send_email`).

---

## 4. Sistema di cache

**Esito:** non esiste.

- `grep -niE 'cache' server.py` → 0 match.
- Nessun modulo `cache.py` nel repo.
- `requirements.txt` non include alcuna libreria di caching.
- Nessuna env var `*_CACHE_*` documentata.

**Conseguenza:** ogni invocazione di tool che ha bisogno di anagrafica (es. `create_invoice` chiama `get_client_by_id` e `get_ei_code_for_client` per costruire l'entity) effettua una chiamata API live a FattureInCloud. Più precisamente:

- `build_entity_from_client(client_id)` chiama `get_client_by_id(client_id)` → API `clients_api.get_client(...)` (server.py:54).
- `get_ei_code_for_client(client_id)` chiama anche lui `get_client_by_id` (server.py:62) → seconda chiamata per lo stesso client_id.
- Su `create_invoice` la stessa anagrafica può essere fetchata due volte in un singolo flusso.

---

## 5. Cost / revenue centers

**Esito:** non esposti.

- `grep -niE 'cost_cent|revenue_cent' server.py` → 0 match.
- Nessun tool `list_cost_centers`.
- `create_invoice`, `create_credit_note`, `create_proforma`, `convert_proforma_to_invoice`, `update_document`: nessun parametro `revenue_center`.
- `list_received_documents` (l'unico tool sui documenti passivi): nessun parametro `cost_center`. Inoltre mancano `get_received_document` e `create_received_document` — il flow received è solo "list".

---

## 6. Drift README ↔ codice

**Esito:** allineato.

- Codice: 20 tool (vedi § 3).
- README.md sezione "Funzionalità (20 tool)" e "Features (20 tools)": entrambe elencano gli stessi 20 nomi del codice.
- Nessuna discrepanza di naming, descrizione corta o presenza/assenza.

---

## 7. SDK MCP

| Campo | Valore |
|---|---|
| Pacchetto | `mcp` (SDK ufficiale low-level Python) |
| Pin in `requirements.txt` | `mcp>=1.0.0` |
| Pattern utilizzato | Server raw + decoratori `@app.list_tools()` / `@app.call_tool()` |
| Import | `from mcp.server import Server`, `from mcp.server.stdio import stdio_server`, `from mcp.types import Tool, TextContent` |
| FastMCP | non usato |

**Versione installata:** non determinabile in questo audit (no venv attivo, requirements solo con floor `>=1.0.0`).

**Note:**
- L'SDK low-level espone già il campo `annotations` su `Tool` (parte della spec MCP 2024-11+). Eventuale aggiunta delle annotations è puramente dichiarativa, no rifattorizzazione.
- Migrazione a FastMCP non necessaria. Il pattern attuale è valido.

---

## 8. Test coverage

**Esito:** 0%.

- Nessuna directory `tests/`.
- Nessun file `test_*.py` o `*_test.py` nel repo.
- `requirements.txt` non include `pytest`/`pytest-cov`/altro framework di test.
- Nessun workflow CI in `.github/`.

---

## 9. Issue GitHub

| # | Stato | Titolo |
|---|---|---|
| 3 | closed (2026-05-10) | "Add page and per_page in list_invoices tool and multi page in get_situation" — chiusa come candidata per release futura |
| 2 | open | "🎨 PREA was here — discovered fattureincloud-mcp" — non actionable |

**Pull Request aperte:** nessuna.

---

## 10. Architettura e struttura repo

```
fattureincloud-mcp/
├── .env.example          # FIC_ACCESS_TOKEN, FIC_COMPANY_ID, FIC_SENDER_EMAIL
├── .gitignore            # include .env, venv/, .venv/, __pycache__, build/, dist/, ecc.
├── CHANGELOG.md          # storia v1.1.0 → v1.8.0 (gap v1.7.x non documentato)
├── LICENSE               # MIT
├── README.md             # bilingue IT/EN, ~280 righe, 20 tool documentati allineati al codice
├── pyproject.toml        # version=1.8.0
├── requirements.txt      # fattureincloud-python-sdk>=2.0.0, mcp>=1.0.0, python-dotenv>=1.0.0
├── server.json           # presente, da indagare in fase di pianificazione
└── server.py             # 1182 righe, monolitico
```

**Funzioni in `server.py`:**

```
44   get_total_from_doc
52   get_client_by_id
60   get_ei_code_for_client      (chiama get_client_by_id → potenziale doppio fetch)
75   build_entity_from_client    (chiama get_client_by_id + get_ei_code_for_client)
99   build_items_list
116  build_issued_document
177  list_tools (decorator MCP)
472  call_tool (decorator MCP)   → 700 righe di if/elif name == "..." per dispatch
1175 main (entry point asyncio)
```

**Pattern dispatch:** `call_tool` è uno switch monolitico su `name`. Spezzare in moduli `tools/*.py` è un'opzione futura, opzionale.

---

## 11. Convenzioni env var

| Variabile | Codice (server.py:27-29) |
|---|---|
| Token API | `FIC_ACCESS_TOKEN` |
| Company ID | `FIC_COMPANY_ID` |
| Email mittente | `FIC_SENDER_EMAIL` |

Prefisso `FIC_*` stabilito su PyPI v1.8 e nel README. Eventuali nuove env var (es. cache) seguiranno la stessa convenzione.

---

## 12. Bug noto duplicate-fattura

- `grep -niE 'TODO|FIXME|XXX|HACK' server.py` → 0 match. Nessun marker nel codice.
- `duplicate_invoice` è definito a server.py:365 (Tool) e server.py:867 (handler).
- v1.3.0 CHANGELOG: "FIX: `duplicate_invoice` aggiorna `ei_code`" (correzione passata).
- Nessuna issue GitHub aperta o chiusa che descrive il bug "cliente specifico" segnalato in fase di pianificazione.

**Conclusione:** senza dati cliente concreti (anagrafica, ID fattura sorgente, errore esatto, log) la riproduzione non è realistica. Tracciato come known issue parcheggiato.

---

## 13. Gap analysis vs scope pianificato

Stato di ciascuna voce dello scope tematico previsto per la prossima release (cache + cost centers + test framework):

| Voce | Stato attuale | Azione necessaria |
|---|---|---|
| Cache file-based | Assente | Da implementare ex novo |
| Wrap fetch anagrafica con decoratore cache | Assente | Da implementare (target: `get_client_by_id`, `get_ei_code_for_client`) |
| Tool `list_cost_centers` | Assente | Da implementare |
| Param `revenue_center` su issued docs | Assente | Da implementare su `create_invoice`/`create_credit_note`/`create_proforma`/`convert_proforma_to_invoice`/`update_document`/`duplicate_invoice` |
| Param `cost_center` su received docs | Assente; mancano anche `get_received_document` e `create_received_document` | Da implementare (estensione completa del flow received per simmetria) |
| Test end-to-end cost centers | Assente (no test affatto) | Da implementare stack pytest + e2e |
| Test regressione cache (drop chiamate API) | Assente | Da implementare |
| Tag git su release | Mai usato in storia | Da introdurre (anche retroattivo per `v1.8.0`) |

---

*Audit prodotto in modalità sola-lettura. Nessuna modifica al codice. Nessun branch creato.*
