---
name: export-erd-drawdb
description: ERD do projeto em formato drawDB. Fonte de verdade em backend/erd.json. Use quando o usuário pedir o ERD para drawdb.app, consultar ou editar o diagrama, incluir ou alterar extensões JSON (ex. tables[].constraints) ou o formato compatível com https://www.drawdb.app/ e https://drawdb-io.github.io/docs/
---

# Exportar ERD no formato JSON do drawDB

## Objetivo

A fonte de verdade do ERD do projeto é `backend/erd.json` (formato JSON do [drawDB](https://www.drawdb.app/)). O restante do sistema deve ser atualizado conforme o conteúdo de `erd.json`.

## Quando usar

- Usuário pede para consultar ou editar o ERD no drawDB.
- Usuário pede para **incluir ou alterar** entradas em `tables[].constraints` em `backend/erd.json`.
- Usuário pede para **incluir ou alterar** metadados por coluna em `tables[].fields[]` (ex.: `nullIfEmpty`).
- Referência ao formato e à localização do diagrama (fonte de verdade).

## Constraints no `erd.json` (padrão JSON)

- **Onde:** no objeto de cada tabela em `tables[]`, chave opcional `constraints`, **no mesmo nível** que `fields`, `indices`, `comment`, etc. (não dentro de `fields[]`). Convém declarar **depois** do array `fields` dessa tabela para ler colunas já definidas.
- **Tipo:** `constraints` é um **array** de objetos. Cada objeto tem exatamente as chaves **`name`** e **`constraint`**, ambas **string** (não `null`; usar `""` só se o projeto aceitar vazio — o padrão desejado é texto não vazio).
- **`name`:** identificador **curto** da constraint, adequado para uso no banco de dados. **Prefixo obrigatório:** o valor de `name` da própria tabela (o campo `name` do objeto em `tables[]`), seguido de `_` e de um sufixo descritivo em snake_case (ex.: tabela `member` → `member_name_required_unless_pending`, `member_unique_tenant_account`). Se o `name` da tabela tiver `.` (ex.: `core.scope`), normalizar para identificador (ex.: `core_scope_...`). Deve ser **único dentro da mesma tabela**. Pode ser usado diretamente em DDL como `ALTER TABLE ... ADD CONSTRAINT name ...`.
- **`constraint`:** **apenas** a expressão SQL/DDL (ex.: `CHECK (...)`, `UNIQUE (...)`, `UNIQUE (...) WHERE ...`), **sem** descrições em português, explicações ou comentários. Para **coerência com o diagrama**, os nomes de coluna mencionados devem coincidir com algum `fields[].name` **dessa mesma tabela**.
- **Relação com `fields[].check`:** anotação por coluna continua no campo `check` do field; regras que envolvem **várias colunas** da mesma tabela ficam em `constraints`. Opcional: em colunas afetadas, deixar em `check` uma frase curta em português que aponte para a entrada em `constraints`.
- Detalhes e exemplo: [reference.md — Extensão do projeto: constraints](reference.md).

## Extensão do projeto: `fields[].nullIfEmpty`

- **Onde:** dentro do próprio objeto de cada item em `tables[].fields[]`, no mesmo nível de `type`, `default`, `notNull`, `comment`, etc.
- **Tipo:** `boolean`, opcional.
- **Significado:** quando `true`, a aplicação pode converter para `NULL` um valor considerado "vazio" para aquele tipo de dado, **antes do `commit`**.
- **Escopo:** é uma convenção da **camada de aplicação**; não implica trigger, `DEFAULT`, `CHECK` ou qualquer automatismo no banco de dados.
- **Uso recomendado:** marcar apenas campos nullable (`notNull: false`) e apenas quando a semântica do campo realmente tratar o valor vazio como ausência de valor.
- **Regra de geração 1:** se `notNull: true`, o gerador deve **ignorar** `nullIfEmpty`, porque a coluna não aceita `NULL`.
- **Regra de geração 2:** se o field for FK (aparecer como origem em `relationships[]`), o gerador deve **ignorar** `nullIfEmpty`, porque a semântica do valor já é controlada por `notNull` e pela própria FK.
- **Mapeamento de vazio:** depende do `type` da coluna e deve ser centralizado na aplicação. A primeira implementação do projeto usa essa convenção como ponto de configuração e mantém a revisão do mapeamento por tipo no código.
- Detalhes e exemplo: [reference.md — Extensão do projeto: fields[].nullIfEmpty](reference.md).

## Fluxo

1. **Fonte de verdade do diagrama**: `backend/erd.json`. O restante do sistema é atualizado conforme esse arquivo.
2. **Importar no drawDB**: em https://www.drawdb.app/editor usar **File > Import** e escolher `backend/erd.json`. Edições no drawDB podem ser exportadas de volta para manter o arquivo em sincronia.

## Formato JSON (resumo)

O drawDB espera um objeto com:

- `tables`: lista de tabelas (id, name, x, y, fields, comment, indices, color).
- `relationships`: lista de relacionamentos (startTableId, startFieldId, endTableId, endFieldId, cardinality, etc.).
- `notes`: array (pode ser `[]`).
- `subjectAreas`: array (pode ser `[]`).

**Extensões do projeto:**
- em cada objeto de `tables[]`, campo opcional `constraints` (lista de objetos com `name` e `constraint`);
- em cada objeto de `tables[].fields[]`, campo opcional `nullIfEmpty` (`boolean`);
- colunas `sort_order` nas tabelas `field` e `action` (ordem por escopo; ver [reference.md](reference.md)).

Onde colocar, formato e coerência: ver secções *Extensão do projeto: constraints*, *Extensão do projeto: fields[].nullIfEmpty* e *Ordenação: sort_order nas tabelas field e action* em [reference.md](reference.md).

Cada **field** em `tables[].fields` deve ter: `id`, `name`, `type`, `default`, `check`, `primary`, `unique`, `notNull`, `increment`, `comment`. Pode também ter extensões do projeto como `nullIfEmpty`.  
Cada **relationship** deve ter: `id`, `name`, `startTableId`, `startFieldId`, `endTableId`, `endFieldId`, `cardinality`, `updateConstraint`, `deleteConstraint`.

Cardinalidade: `"one_to_one"`, `"one_to_many"`, `"many_to_one"`.  
Constraints de FK: `"No action"`, `"Restrict"`, `"Cascade"`, `"Set null"`, `"Set default"`.

## Referência completa

Para o esquema JSON completo (tipos, enums, áreas, notas), ver [reference.md](reference.md). Documentação oficial: [drawDB Docs](https://drawdb-io.github.io/docs/), [drawDB Editor](https://www.drawdb.app/editor).

## Manutenção

- A fonte de verdade do diagrama é `backend/erd.json`; edições no drawDB ou no repo devem refletir nesse arquivo.

## Tabela `log` e lista de tabelas monitorizadas

- Ao alterar em `backend/erd.json` a lista de valores em `log.table_name` (ou o CHECK equivalente no modelo/migrations), seguir a skill [**audit-log-triggers**](../audit-log-triggers/SKILL.md) para triggers PostgreSQL, contrato `set_config` / `SET LOCAL` e testes opcionais com `VALORA_AUDIT_PG_TEST=1`.
