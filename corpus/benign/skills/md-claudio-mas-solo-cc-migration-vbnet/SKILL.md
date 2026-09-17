---
name: migration-vbnet
description: >
  Analisa arquivos de forms VB.Net (.vb, .Designer.vb, .resx) e produz os
  artefatos de migração para a stack web do projeto Solo Consultoria de Imóveis
  (FastAPI + React + SQL Server). Use esta skill SEMPRE que o usuário mencionar
  arquivos .vb, .Designer.vb ou .resx, fizer referência a um form legado
  (ex: frmLogin, FrmPrincipal), pedir análise de regras de negócio do sistema
  desktop, solicitar geração de endpoint FastAPI ou componente React equivalente
  a uma tela do sistema antigo, ou quando arquivos estiverem na pasta
  legacy/forms/. Ative também para perguntas sobre rastreabilidade entre telas
  web e forms originais, mesmo que os arquivos não estejam anexados na conversa.
---

# Skill: migration-vbnet

Guia completo para analisar forms VB.Net e produzir os quatro artefatos de
migração do projeto Solo Consultoria de Imóveis.

---

## Contexto do Projeto

- **Sistema original:** Desktop VB.Net + SQL Server (Contas Correntes)
- **Destino:** React (frontend) + FastAPI Python (backend) + SQL Server mantido
- **Schema do banco:** Não alterar sem aprovação — apenas leitura/escrita
- **Senhas:** Sempre bcrypt no código novo — nunca texto plano
- **Referência legado:** `legacy/forms/` na raiz do monorepo (somente leitura)

---

## Entrada Esperada

O usuário deve fornecer os três arquivos do form:

| Arquivo | Conteúdo extraído |
|---|---|
| `NomeForm.vb` | Eventos, validações, lógica de negócio, chamadas ao banco |
| `NomeForm.Designer.vb` | Controles, propriedades visuais, layout, tab order |
| `NomeForm.resx` | Strings, labels, imagens embarcadas |

Se apenas um ou dois arquivos forem fornecidos, trabalhe com o que há e
sinalize o que não pôde ser inferido.

Se um print do form for fornecido, use-o para confirmar hierarquia visual,
agrupamento de seções e ordem de leitura — informações que o Designer às vezes
não deixa óbvias.

---

## Processo de Análise

### 1. Leitura e inventário

Ao receber os arquivos, extraia:

**Do `.Designer.vb`:**
- Todos os controles declarados e suas propriedades relevantes (Name, Text,
  TabIndex, Visible, Enabled, PasswordChar, DataSource, DisplayMember, etc.)
- Hierarquia de painéis, abas (TabControl) e grupos
- Controles com `Visible = False` → documentar mas não migrar para a UI
- Ordem de tab (TabIndex) → define a ordem de foco nos campos do webform

**Do `.vb`:**
- Todos os eventos e sua lógica (Load, Click, KeyDown, TextChanged, etc.)
- Variáveis globais lidas ou escritas (`varUsu`, `varPerfil`, etc.)
- Queries ao banco (LINQ, SQL direto, TableAdapter)
- Fluxo de navegação (quais forms são abertos/fechados)
- Blocos comentados → documentar separadamente com flag de decisão pendente

**Do `.resx`:**
- Strings de UI não óbvias no Designer
- Imagens → registrar como assets a substituir (logo, ícones)

### 2. Identificação de regras de negócio

Numere cada regra no formato `RNxx` sequencial dentro do form analisado.
Classifique cada uma:

| Tipo | Exemplos |
|---|---|
| Validação | Campo obrigatório, formato, range |
| Autenticação / Autorização | Login, perfil, permissão por tela |
| Cálculo | Saldo, totais, datas |
| Fluxo | Qual tela abre após ação, condições de habilitação |
| Dados | Como a lista é carregada, ordenação, filtros |
| UX | Comportamento de foco, limpeza de campo após erro |
| Apresentação | Formatação de valores, maiúsculas, cores condicionais |

### 3. Atenção a padrões recorrentes no sistema

Consulte `references/padroes-legado.md` para os padrões já mapeados no
sistema (TableAdapter, variáveis globais, navegação entre forms, etc.) e
verifique se o form atual os utiliza.

---

## Saídas a Produzir

Produza sempre os quatro artefatos, nesta ordem:

### Artefato 1 — Documentação funcional (`NomeForm_documentacao.md`)

Estrutura obrigatória:
1. Visão geral (o que o form faz em 2–3 frases)
2. Tabela de componentes visuais (controle, tipo, label, descrição)
3. Estrutura de dados (tabelas SQL envolvidas, campos usados)
4. Fluxo de execução (por evento — use diagrama ASCII para fluxos de decisão)
5. Tabela de regras de negócio (ID, descrição, tipo)
6. Variáveis globais lidas/escritas
7. Observações para a migração (alertas, decisões pendentes, itens comentados)

### Artefato 2 — Router FastAPI (`nome_router.py`)

Convenções obrigatórias:
- Arquivo em `backend/app/routers/`
- `APIRouter` com `prefix` e `tags` correspondentes ao domínio do form
- Um endpoint por operação do form (carregar dados, submeter, etc.)
- Cada endpoint deve ter `summary` e `description` no decorator
- Docstrings internos referenciando as RNs implementadas (`# RN03 — ...`)
- Schemas Pydantic para request e response (incluir no mesmo arquivo ou
  indicar que devem ir para `backend/app/schemas/`)
- Lógica de negócio extraída para `backend/app/services/` — routers só
  orquestram
- `Depends(get_current_user)` em todos os endpoints que exigem autenticação
- Queries via SQLAlchemy — nunca concatenação de string SQL
- Nunca `SELECT *` — sempre listar colunas explicitamente
- Tratamento de exceções com `HTTPException` e códigos HTTP apropriados
- Variáveis de ambiente para connection strings — nunca hardcoded

### Artefato 3 — Componente React (`NomeForm/index.jsx`)

Convenções obrigatórias:
- Arquivo em `frontend/src/pages/NomeForm/index.jsx`
- Chamadas à API exclusivamente via `frontend/src/services/` — nunca `fetch`
  direto no componente
- Replicar exatamente o comportamento de foco e validação do form original
  (RNs de UX devem ter implementação equivalente)
- Campos de senha sempre `type="password"`
- ComboBox com autocomplete → `<input>` + `<datalist>` ou select controlado
- Controles com `Visible = False` no original → não renderizar (ou renderizar
  com `display: none` apenas se houver lógica futura prevista)
- Token JWT em `localStorage` com as chaves `access_token`, `perfil`, `usuario`
- Estilos inline apenas como placeholder — adicionar comentário indicando
  substituição por Tailwind/CSS Modules conforme design system
- Loading state para operações assíncronas
- Mensagens de erro fiéis às do form original (mesmo texto, quando possível)

### Artefato 4 — Atualização da tabela de rastreabilidade

Fornecer a linha a ser adicionada no `CLAUDE.md`:

```markdown
| `/rota-web` | `NomeFormOriginal` | `docs/NomeForm_documentacao.md` |
```

---

## Alertas Automáticos

Sempre que identificar os itens abaixo, sinalize com ⚠️ antes de prosseguir:

- **Senha em texto plano** — nunca replicar; usar bcrypt + indicar necessidade
  de script de migração de dados
- **Variável global** — indicar o equivalente web (JWT claim, contexto React,
  estado global)
- **Bloco de código comentado** — documentar e marcar como "decisão pendente"
  com o responsável pelo sistema
- **Query SQL sem parâmetros** (concatenação de string) — reescrever com
  parâmetros no FastAPI
- **`Application.Exit()`** — equivalente web é `window.close()` ou redirect,
  dependendo do contexto; alertar sobre diferença de comportamento
- **Múltiplos TableAdapters Fill no Load** — verificar se há chamada duplicada
  (padrão encontrado no frmLogin)
- **Referência a outro form** (`FrmXxx.Show()`) — mapear dependência e
  verificar se o form de destino já foi migrado

---

## Referências

Leia o arquivo abaixo quando encontrar padrões do sistema legado que precisam
de mapeamento padronizado:

→ `references/padroes-legado.md` — padrões VB.Net recorrentes e seus
equivalentes na stack web do projeto