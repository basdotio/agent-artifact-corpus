---
name: forja-backend-engineer
description: Skill obrigatória para qualquer tarefa de backend do FORJA. Use sempre que a solicitação envolver edição, criação, revisão ou análise de arquivos em backend/**/*.go, backend/internal/**, backend/migrations/** ou backend/cmd/**. Carregue esta skill antes de raciocinar sobre implementação para garantir Clean Architecture, DDD, multi-tenant isolation, SQLC, RBAC e segurança de produção.
---

# SKILL NAME

forja-backend-engineer

# PURPOSE

Esta skill garante que qualquer mudança de backend no FORJA siga a arquitetura, regras e padrões oficiais do projeto.

Ela orienta a IA a implementar features em Go com segurança, respeitando Clean Architecture, multi-tenancy, uso de SQLC, enforcement de RBAC e domain-driven design.

Use esta skill sempre que a IA editar:

- `backend/**/*.go`
- `backend/internal/**`
- `backend/migrations/**`
- `backend/cmd/**`

# PROJECT CONTEXT

FORJA é uma plataforma SaaS multi-tenant para gestão de barbearias.

Princípios de arquitetura:

- Clean Architecture
- Domain Driven Design
- Multi-tenant SaaS
- Backend em Go
- SQLC para acesso a banco
- Echo v4 como framework HTTP

Stack atual:

Backend:

- Go 1.24
- Echo v4
- SQLC
- pgx/v5
- Zap logger

Database:

- PostgreSQL 16 (Neon)

Infrastructure:

- Fly.io

O sistema está na fase de Hardening & Polishing (Q1 2026) e já roda em produção.

# REQUIRED PRE-READ (MANDATORY)

Antes de qualquer alteração de backend, leia obrigatoriamente:

- `docs/ESTADO_ATUAL_DO_SISTEMA.md`
- `.github/copilot-instructions.md`
- `.github/ai/AI_OPERATOR_CORE.md`

Esses arquivos são a fonte de verdade de arquitetura e comportamento do sistema.

# BACKEND ARCHITECTURE

A arquitetura segue Clean Architecture estrita:

Presentation -> Application -> Domain -> Infrastructure

Regras:

Domain:

- regras de negócio puras
- sem dependências externas

Application:

- use cases
- orquestra lógica de domínio

Presentation:

- handlers Echo
- mapeamento de DTO

Infrastructure:

- implementações de repositório
- queries SQLC
- provedores externos

Handlers NÃO podem conter lógica de negócio.

# MULTI TENANCY RULES

O sistema é multi-tenant.

Regras:

- `tenant_id` vem somente de claims do JWT
- `tenant_id` nunca vem do payload da requisição
- toda query filtra por `tenant_id`
- joins cross-tenant são proibidos

Quebra de isolamento entre tenants é bug crítico.

# DATABASE RULES

Acesso ao banco segue restrições rígidas:

- SQL deve ser escrito em arquivos SQLC
- nunca escrever SQL inline em Go
- todas as tabelas devem ter `tenant_id`
- todo `SELECT/UPDATE/DELETE` deve filtrar `tenant_id`

Valores financeiros:

- usar `NUMERIC(18,2)` exclusivamente
- nunca usar `float`

# USE CASE PATTERN

Todo use case deve seguir a estrutura:

1. Validar tenant
2. Validar RBAC
3. Abrir transação quando necessário
4. Chamar repositórios por interfaces
5. Aplicar regras de domínio
6. Retornar DTO

Handlers devem somente:

bind -> validate -> call use case -> map DTO

Nunca colocar lógica de negócio no handler.

# ERROR RESPONSE PATTERN

Erros da API devem seguir este formato:

```json
{
  "code": "ERR_CODE",
  "message": "Mensagem clara em pt-BR",
  "details": {},
  "request_id": "uuid"
}
```

Códigos permitidos:

- `ERR_VALIDATION`
- `ERR_FORBIDDEN`
- `ERR_NOT_FOUND`
- `ERR_CONFLICT`
- `ERR_EXTERNAL_PROVIDER`
- `ERR_INTERNAL`

# TRANSACTION RULE

Transação é obrigatória quando:

- múltiplas escritas ocorrem
- fechamento de pedido
- movimentação de estoque
- lançamento financeiro

Use fronteiras explícitas de transação.

# SECURITY RULES

Autenticação:

- JWT HS256

RBAC roles:

- OWNER
- MANAGER
- BARBER
- RECEPTIONIST
- ACCOUNTANT

Permissão de leitura financeira:

- OWNER
- MANAGER
- ACCOUNTANT

Permissão de escrita financeira:

- OWNER
- MANAGER

# PROHIBITED ACTIONS

Recusar explicitamente:

- SQL inline em Go
- `tenant_id` em payload de requisição
- lógica de negócio em handlers
- `float` para valores financeiros
- acesso a banco fora de repositórios
- bypass de validação RBAC
- edição direta de banco de produção

# OUTPUT STYLE

Ao implementar mudanças de backend:

1. Explicar impacto arquitetural
2. Identificar camadas afetadas
3. Implementar respeitando limites entre camadas
4. Garantir segurança de tenant
5. Garantir enforcement de RBAC

# ACTIVATION RULE

Se a tarefa envolver qualquer arquivo dentro de `backend/`, carregue esta skill antes de qualquer raciocínio de implementação.

Se esta skill ainda não tiver sido carregada, interrompa o fluxo, carregue a skill e só então prossiga.
