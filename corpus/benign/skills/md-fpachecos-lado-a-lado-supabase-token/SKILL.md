---
name: supabase-token
description: "Renova o Supabase Personal Access Token via navegador e atualiza o .env automaticamente."
---

# supabase-token

Renova o `SUPABASE_ACCESS_TOKEN` no Supabase Dashboard via automação de navegador e atualiza o `.env` do projeto.

## Comportamento

Quando o usuário invocar `/supabase-token`:

### 1. Verifique o token atual

Leia o `.env` e verifique a data de expiração do token atual listado no Supabase:

```bash
grep SUPABASE_ACCESS_TOKEN /Users/fipacheco/lado-a-lado/.env
```

### 2. Abra o Supabase Dashboard via navegador

Use as ferramentas de browser para:

1. Obter contexto de abas com `tabs_context_mcp`
2. Navegar para `https://supabase.com/dashboard/account/tokens` em uma aba nova ou existente
3. Fazer screenshot para confirmar que a página carregou

### 3. Revogue o token antigo (opcional)

Localize o token "Claude Code CLI" na lista e clique no menu `⋮` → **Revoke** para removê-lo, evitando acúmulo de tokens expirados.

> Pule esta etapa se o token antigo já estiver expirado ou não aparecer na lista.

### 4. Gere o novo token

1. Clique em **Generate new token**
2. No modal que abrir:
   - Nome: `Claude Code CLI`
   - Expiração: **30 days**
3. Clique em **Generate token**
4. Copie o valor exibido (começa com `sbp_`) — ele só aparece uma vez

### 5. Atualize o .env

Substitua o valor de `SUPABASE_ACCESS_TOKEN` no `.env`:

```
/Users/fipacheco/lado-a-lado/.env
```

Use o Edit tool para substituir a linha existente pelo novo valor.

### 6. Re-linke o projeto

O projeto precisa ser re-linkado após trocar o token:

```bash
SUPABASE_ACCESS_TOKEN=<novo_token> npx supabase link --project-ref xstsbaexisgxebgydtyj 2>&1
```

### 7. Confirme que está funcionando

Teste a conexão com uma query simples:

```bash
SUPABASE_ACCESS_TOKEN=$(grep SUPABASE_ACCESS_TOKEN /Users/fipacheco/lado-a-lado/.env | cut -d= -f2-) \
npx supabase db query --linked --agent=yes \
  "SELECT table_name FROM information_schema.tables WHERE table_schema = 'ladoalado' ORDER BY table_name;" 2>&1
```

Se retornar as 4 tabelas (`babies`, `visit_bookings`, `visit_schedules`, `visit_slots`), o token está funcionando corretamente.

## Informações do projeto

- **Project ref:** `xstsbaexisgxebgydtyj`
- **Dashboard de tokens:** `https://supabase.com/dashboard/account/tokens`
- **Token atual expira em:** 20 Abr 2026 (gerado em 21 Mar 2026)
