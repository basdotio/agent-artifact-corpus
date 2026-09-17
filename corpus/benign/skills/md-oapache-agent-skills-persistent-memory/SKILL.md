---
name: persistent-memory
description: Salva e recupera memória persistente em MEMORY.md e memory/YYYY-MM-DD.md, separando fatos duráveis de contexto operacional.
version: 1.0.0
metadata:
 openclaw:
 emoji: "🧠"
 requires:
 bins: []
 homepage: "https://github.com/seu-user/persistent-memory"
---

# Persistent Memory

Use esta skill quando a tarefa exigir continuidade entre sessões, retenção de preferências, recuperação de decisões anteriores ou acompanhamento de trabalho em andamento.

## Objetivo

Manter memória persistente de forma disciplinada, separando:
- memória durável de longo prazo
- contexto operacional de curto prazo

## Arquivos de memória

### Longo prazo
Use `MEMORY.md` para:
- preferências estáveis do usuário
- decisões importantes
- fatos duráveis
- convenções de projeto
- contexto que precisa sobreviver por muito tempo

### Curto prazo
Use `memory/YYYY-MM-DD.md` para:
- progresso do dia
- tarefas em andamento
- resultados parciais
- observações temporárias
- próximos passos
- bloqueios

## Regras principais

1. Antes de perguntar algo já conhecido, procurar em memória.
2. Antes de iniciar trabalho contínuo, recuperar contexto relevante.
3. Se o usuário disser "lembre disso" ou equivalente, gravar imediatamente.
4. Salvar em `MEMORY.md` apenas fatos duráveis.
5. Salvar em `memory/YYYY-MM-DD.md` contexto temporário e progresso operacional.
6. Não duplicar memórias sem necessidade.
7. Ao final de tarefas longas, registrar:
 - o que foi feito
 - o que falta
 - decisões tomadas
 - próximos passos
8. Nunca confiar apenas no contexto da sessão para algo que precisa persistir.

## Fluxo de uso

### 1. Recuperar
Quando a tarefa depender de histórico:
- usar `memory_search` para localizar memórias relevantes
- usar `memory_get` para ler o trecho ou arquivo certo
- resumir internamente o que é útil antes de agir

### 2. Classificar
Antes de salvar, decidir:
- isso é durável? → `MEMORY.md`
- isso é operacional e temporário? → `memory/YYYY-MM-DD.md`

### 3. Persistir
Ao gravar:
- escrever de forma curta e objetiva
- usar bullets
- incluir data quando útil
- evitar texto redundante
- preferir atualização incremental em vez de reescrever tudo

### 4. Consolidar
Quando algo temporário virar conhecimento estável:
- promover do log diário para `MEMORY.md`

## Heurísticas de classificação

Salvar em `MEMORY.md`:
- "O usuário prefere MiniMax como modelo principal"
- "Projeto usa PostgreSQL com Prisma"
- "Decisão: usar filas com BullMQ"

Salvar em `memory/YYYY-MM-DD.md`:
- "Hoje foi criado o endpoint /tasks"
- "Erro no deploy por variável ausente"
- "Próximo passo: revisar autenticação"

## Formato sugerido para MEMORY.md

```md
# Memory

## User preferences
- ...

## Project decisions
- ...

## Stable facts
- ...
```
