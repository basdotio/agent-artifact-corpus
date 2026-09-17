---
name: clickup-master
description: Agente MASTER do ClickUp. Use para qualquer operação no ClickUp: criar tarefas, projetos, workspaces, diagnosticar bloqueios, gerenciar atribuições, gerar relatórios e executar comandos via linguagem natural. Combina operações diretas pela API v2, criação de tickets com padrões de qualidade e gerenciamento avançado de projetos. Gatilhos: 'criar tarefa no ClickUp', 'criar projeto', 'status do projeto', 'quem está bloqueando', 'adicionar membro', 'criar workspace', 'ticket ClickUp', 'diagnóstico ClickUp', 'listar tarefas', 'atualizar status', 'time tracking ClickUp', 'relatório ClickUp', 'alocar time'.
---

# ClickUp MASTER Agent

Agente unificado para todas as operações do ClickUp. Combina o melhor de três skills do repositório `openclaw/skills`:
1. **clickup-operational** (aiwithabidi) — Operações determinísticas, parsing de linguagem natural, diagnósticos
2. **clickup-ticket-manager** (niyol) — Criação de tickets com padrões de qualidade
3. **clickup-project-management** (taazkareem) — Gerenciamento avançado via MCP Server

---

## Credenciais

```python
# Via workspace-credentials skill:
import os, sys
sys.path.insert(0, r"C:\Users\Pichau\Documents\Skills")
from load_credentials import load_env, get_required
load_env()

CLICKUP_API_TOKEN = get_required("CLICKUP_API_TOKEN")  # Token pessoal (pk_...)
BASE_URL = "https://api.clickup.com/api/v2"
HEADERS = {"Authorization": CLICKUP_API_TOKEN, "Content-Type": "application/json"}
```

**Variáveis necessárias no `.env.master`:**
| Variável | Descrição |
|----------|-----------|
| `CLICKUP_API_TOKEN` | Personal API Token (`pk_...`) |
| `CLICKUP_DEFAULT_LIST_ID` | ID da lista padrão para tickets |
| `CLICKUP_DEFAULT_STATUS` | Status padrão (`BACKLOG`) |
| `CLICKUP_DEFAULT_TAG` | Tag padrão (`automated`) |

---

## Filosofia Central

**Operações Determinísticas** — Cada comando confirma sucesso com detalhes ou falha com erro explícito. Zero estados ambíguos. Validação completa a cada passo.

**Padrão de execução:**
1. Validar inputs → 2. Verificar pré-condições → 3. Executar API → 4. Verificar resultado → 5. Confirmar sucesso

---

## Capacidades Operacionais

### 1. Criação de Tarefas (Tickets com Qualidade)

**Prioridades:**
| Palavra | Valor API |
|---------|-----------|
| urgent | 1 |
| high | 2 |
| normal | 3 |
| low | 4 |

```python
import requests, time

def create_task(list_id, title, description, priority=None, status="BACKLOG", tags=None):
    """Cria tarefa com padrões de qualidade. Descrição mínimo 2-3 frases."""
    assert title, "Título é obrigatório"
    assert description and len(description) > 30, "Descrição muito curta (mín 2-3 frases)"
    
    payload = {
        "name": title,
        "description": description,
        "status": status,
        "tags": tags or ["automated"],
    }
    if priority:
        payload["priority"] = priority  # 1=urgent, 2=high, 3=normal, 4=low
    
    r = requests.post(f"{BASE_URL}/list/{list_id}/task", json=payload, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    return {"id": data["id"], "url": data["url"], "created": True}
```

---

### 2. Parsing de Linguagem Natural → Operações Estruturadas

```
Input: "Cria projeto para Acme Corp com fases de onboarding, design e retainer"
Parse:
  - workspace: Delivery
  - cliente: Acme Corp
  - estrutura: folder → 3 listas (onboarding, design, retainer)
  - responsáveis: detectar por nome no workspace
  - datas: inferir das fases
  
Executa: sequência determinística com rollback em falha
Confirma: "Projeto Acme Corp criado: 3 fases, 12 tarefas"
```

**Exemplos de comandos suportados:**
- `"Cria projeto para [cliente] com [fases]"`
- `"O que está bloqueando [projeto]?"`
- `"Coloca [pessoa] na tarefa [Y]"`
- `"Qual o status de [projeto]?"`
- `"Gera tarefas técnicas para [projeto]"`
- `"Quantas horas o time logou essa semana?"`
- `"Aloca [time] no [projeto] com capacidade [X]h/semana"`

---

### 3. Diagnóstico de Projetos

```python
def diagnose_project(folder_id: str) -> dict:
    """Escaneia todas as tarefas e identifica bloqueios, atrasos e lacunas."""
    tasks = get_all_tasks(folder_id)
    now_ms = int(time.time() * 1000)
    
    blocked    = [t for t in tasks if t["status"]["status"] in ("blocked", "waiting")]
    overdue    = [t for t in tasks if t.get("due_date") and int(t["due_date"]) < now_ms 
                  and t["status"]["status"] != "complete"]
    no_assignee = [t for t in tasks if not t.get("assignees")]
    
    return {
        "blocked":     [(t["name"], t.get("text_content","")) for t in blocked],
        "overdue":     [(t["name"], t["due_date"])            for t in overdue],
        "no_assignee": [t["name"]                            for t in no_assignee],
        "total":       len(tasks),
        "complete":    len([t for t in tasks if t["status"]["status"] == "complete"]),
    }
```

**Saída exemplo:**
```
📊 Projeto: Acme Corp — 8/15 tarefas concluídas
🚫 Bloqueadas: 3 (aguardando edição de vídeo)
⏰ Atrasadas: 2
👤 Sem responsável: 1 (urgente!)
📅 ETA estimado: +5 dias
```

---

### 4. Templates de Workspace

| Palavra-chave | Estrutura Criada |
|---------------|------------------|
| `website / site` | Design → Dev → QA → Launch |
| `imobiliário` | Pesquisa → Design → Build → Launch |
| `onboarding` | Kickoff → Setup → Training → Go-live |
| `agência` | Brief → Produção → Revisão → Entrega |
| `produto` | Discovery → Spec → Dev → Release |

---

### 5. Geração de Tarefas Técnicas

```
Input: "Quebra o projeto de website da Clarify em tarefas técnicas"
Gera (com estimativas, responsáveis e dependências):
- Setup Git + CI/CD
- Dependências npm
- Componentes: Home, About, Contact
- Formulário com validação
- SEO: sitemap.xml, robots.txt
- Auditoria Lighthouse
- Deploy Vercel
- Configurar analytics
```

---

### 6. Orquestração de Atribuições

```
Input: "Coloca Carlos e Ana na tarefa de onboarding do Kortex"
→ Busca membros → Localiza tarefa → Atribui → Comenta @Carlos @Ana
→ Define prazo +3d, prioridade alta, status "in progress"
→ Confirma com URL
```

---

## API ClickUp v2 — Referência Rápida

```
Base URL: https://api.clickup.com/api/v2
Auth: Header "Authorization: {CLICKUP_API_TOKEN}"
Rate Limit: 100 req/min
```

| Operação | Método | Endpoint |
|----------|--------|----------|
| Listar workspaces | GET | `/team` |
| Listar spaces | GET | `/team/{team_id}/space` |
| Criar space | POST | `/team/{team_id}/space` |
| Listar folders | GET | `/space/{space_id}/folder` |
| Criar folder | POST | `/space/{space_id}/folder` |
| Listar listas | GET | `/folder/{folder_id}/list` |
| Criar lista | POST | `/folder/{folder_id}/list` |
| Listar tarefas | GET | `/list/{list_id}/task` |
| Criar tarefa | POST | `/list/{list_id}/task` |
| Atualizar tarefa | PUT | `/task/{task_id}` |
| Deletar tarefa | DELETE | `/task/{task_id}` |
| Adicionar membro | POST | `/task/{task_id}/member` |
| Comentar | POST | `/task/{task_id}/comment` |
| Time tracking | POST | `/task/{task_id}/time` |
| Membros | GET | `/team/{team_id}/member` |
| Custom fields | GET | `/list/{list_id}/field` |

---

## Tratamento de Erros

| Código | Erro | Ação |
|--------|------|------|
| 401 | Token inválido | Verificar `CLICKUP_API_TOKEN` |
| 403 | Sem permissão | Verificar acesso ao workspace |
| 404 | Não encontrado | Verificar IDs |
| 429 | Rate limit | Retry com backoff (`Retry-After` header) |
| 400 | Dados inválidos | Retornar erros por campo |

```python
def api_call(method, endpoint, payload=None, retries=3):
    for attempt in range(retries):
        r = requests.request(method, f"{BASE_URL}{endpoint}", json=payload, headers=HEADERS)
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", 60)) + 1
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()
```

---

## Integração com n8n

- Node **HTTP Request** com `Authorization: {{$env.CLICKUP_API_TOKEN}}`
- Para webhooks do ClickUp, usar node **Webhook**
- Ver skill `n8n-workflow-patterns` para padrões

---

## Skills Relacionadas

- **workspace-credentials** — `CLICKUP_API_TOKEN`
- **n8n-mcp-tools-expert** — Automações n8n + ClickUp
- **n8n-workflow-patterns** — Padrões de integração
- **skill-creator** — Estender este agente

---

## Fontes (openclaw/skills)

| Skill | Autor | Contribuição Principal |
|-------|-------|----------------------|
| `clickup-operational` | aiwithabidi | NL parsing, diagnósticos, workspace templates, determinismo |
| `clickup-ticket-manager` | niyol | CLI tickets, prioridades, padrões de qualidade |
| `clickup-project-management` | taazkareem | MCP Server premium (requer `CLICKUP_MCP_LICENSE_KEY`) |
