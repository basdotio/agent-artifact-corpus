---
name: e2e-testing
description: Skill para criação de testes E2E com Playwright seguindo as melhores práticas e padrões do projeto Aereo.
---

# Skill: Testes E2E com Playwright

Esta skill orienta a criação de testes end-to-end (E2E) para o projeto Aereo. O agente deve focar **exclusivamente** na criação de testes e **NÃO deve alterar código de produção**.

## 🚨 Regras Fundamentais

> [!CAUTION]
> **NUNCA modifique arquivos fora do diretório `tests/`**. Se houver bugs no código de produção, reporte ao usuário e aguarde instruções.

1. **Escopo restrito**: Criar/modificar apenas arquivos em `tests/`
2. **Não corrigir bugs**: Se um teste falhar por bug no app, documente no teste
3. **Fonte da verdade**: Sempre consulte os testes existentes em `tests/` para padrões atuais
4. **Use os resources**: Consulte `resources/` desta skill para templates e metodologias

---

## 📦 Resources Disponíveis

Esta skill inclui recursos em `.agents/skills/e2e-testing/resources/`:

| Arquivo | Descrição |
|---------|-----------|
| `template-flow.spec.ts` | Template para testes de fluxo básico |
| `template-authenticated.spec.ts` | Template para rotas protegidas |
| `helpers.ts` | Funções utilitárias reutilizáveis |
| `selector-patterns.md` | **Padrões e metodologias** para escolha de seletores |

---

## 🔍 Metodologia: Antes de Criar um Teste

> [!IMPORTANT]
> Sempre siga este processo para garantir padrões consistentes.

### 1. Consulte Testes Existentes
```bash
# Verifique se já existe teste para o fluxo
ls tests/

# Examine testes similares para copiar padrões
cat tests/auth/login.spec.ts
```

### 2. Analise a UI Atual
- Navegue até a página que será testada
- Identifique os elementos interativos (botões, inputs, headings)
- Anote os textos/labels exatos que aparecem na UI

### 3. Derive Seletores da UI
Use a ordem de prioridade em `resources/selector-patterns.md` para criar seletores baseados nos elementos reais encontrados.

---

## 📁 Estrutura de Diretórios

```
tests/
├── auth/              # Fluxos de autenticação
├── ui/                # Componentes isolados
├── setup/             # Scripts de configuração
│   ├── reset.ts       # Limpa o banco de testes
│   └── seed.ts        # Popula dados de teste
└── [feature].spec.ts  # Novos fluxos
```

---

## ⚙️ Ambiente de Testes

### Configuração (ver `playwright.config.ts`)
- **Porta da aplicação**: Definida em `baseURL`
- **Banco de dados**: Ver `.env.test` e `docker-compose.test.yml`
- **Browser**: Configurado em `projects`

### Comandos (ver `package.json` para lista atualizada)

```bash
# Subir banco de testes
pnpm docker:test:up

# Resetar e popular dados
pnpm test:e2e:reset

# Executar testes
pnpm test:e2e

# Modo interativo
pnpm test:e2e:ui
```

---

## 📝 Padrão de Escrita de Testes

### Template Básico (ver `resources/template-flow.spec.ts`)

```typescript
import { expect, test } from "@playwright/test";

test.describe("[Nome do Fluxo]", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/rota-inicial");
  });

  test("should [descrever comportamento esperado]", async ({ page }) => {
    // Arrange - preparar estado
    // Act - executar ações
    // Assert - verificar resultados
  });
});
```

---

## ✅ Checklist para Novos Testes

Antes de criar um teste:

- [ ] Verificar se já existe teste similar em `tests/`
- [ ] Analisar a UI atual para descobrir textos/labels reais
- [ ] Identificar dados necessários (existem no `tests/setup/seed.ts`?)
- [ ] Copiar padrões de testes existentes similares
- [ ] Usar seletores semânticos (ver `resources/selector-patterns.md`)
- [ ] Testar em modo UI primeiro: `pnpm test:e2e:ui`

---

## 🎯 Boas Práticas

### DO ✅

```typescript
// Waits implícitos via assertions
await expect(page.getByLabel("Campo")).toBeVisible();

// Nomes descritivos
test("should redirect to dashboard after successful login", ...)

// Dados únicos para evitar conflitos
const testEmail = `user-${Date.now()}@example.com`;

// Verificar estados finais
await expect(page).toHaveURL(/\/rota-esperada/);
```

### DON'T ❌

```typescript
// Sleeps arbitrários
await page.waitForTimeout(3000); // EVITAR

// Seletores frágeis baseados em classes
page.locator(".btn-primary"); // EVITAR

// Dados hardcoded que podem conflitar
const email = "test@test.com"; // PODE CONFLITAR
```

---

## 🧪 Executando Testes

```bash
# Setup inicial (primeira vez)
pnpm docker:test:up && pnpm test:e2e:reset

# Modo headless (CI)
pnpm test:e2e

# Modo interativo (debug)
pnpm test:e2e:ui

# Executar arquivo específico
pnpm test:e2e tests/auth/login.spec.ts

# Executar teste específico
pnpm test:e2e -g "nome do teste"
```

---

## 🔧 Adicionando Dados de Teste

Se o teste precisar de dados que não existem:

1. Edite `tests/setup/seed.ts`
2. Siga o padrão dos dados já existentes
3. Execute `pnpm test:e2e:reset` para aplicar

---

## 🐛 Debug de Testes

```bash
# Executar com browser visível
pnpm test:e2e --headed

# Pausar em falhas
pnpm test:e2e --debug

# Ver relatório HTML após execução
npx playwright show-report
```
