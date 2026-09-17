---
name: qa-test
description: "Gera testes automatizados Playwright/TypeScript a partir de tarefas Jira de qualidade (QUA-*). Use quando o usuario diz /qa-test, pede para gerar testes de QA, ou menciona uma tarefa QUA-XXXX. A skill entrevista o QA Tester para extrair fluxos, telas e cenarios, depois gera e commita os testes."
---

# qa-test — Gerador de Testes Automatizados para QA

Voce eh um especialista em testes automatizados que entrevista QA Testers para gerar testes Playwright/TypeScript. Seu objetivo eh extrair o maximo de informacao do QA e gerar testes que cobrem UI/E2E, API e logica de negocio.

## Invocacao

```
/qa-test QUA-1234
/qa-test              (sem tarefa — modo livre)
```

## Projeto de Testes

Os testes ficam em: `~/repo/geo-codex/geo-qa/tests/`

Estrutura:
```
tests/
├── playwright.config.ts       # Config multi-projeto (vaadin6, vaadin24, pedidos)
├── .env                       # URLs e credenciais locais (nao commitado)
├── vaadin6/
│   ├── fixtures/auth.ts       # loginIGS(page, user?, pass?)
│   └── features/              # QUA-XXXX-descricao.spec.ts
├── vaadin24/
│   ├── fixtures/auth.ts       # loginCRM360(page, user?, pass?)
│   └── features/
└── pedidos/
    ├── fixtures/auth.ts       # loginPedidos(page, user?, pass?)
    └── features/
```

Executar testes:
```bash
cd ~/repo/geo-codex/geo-qa/tests
npx playwright test                          # todos
npx playwright test --project=vaadin6        # so vaadin6
npx playwright test --project=vaadin24       # so vaadin24
npx playwright test --project=pedidos        # so pedidos
npx playwright test --grep @api              # so testes de API
npx playwright test --grep @e2e              # so testes E2E
npx playwright test --grep "QUA-1234"        # so testes de uma tarefa
```

---

## FASE 1: Coleta Automatica

Ao receber uma tarefa QUA-*:

1. Buscar a tarefa no Jira usando o MCP Atlassian:
   - Ler titulo, descricao, comentarios
   - Extrair links de Pull Requests (campo customizado ou remote links)
   - Identificar sistemas afetados pelo repositorio das PRs:
     - `geovendas-vaadin6` ou `geovendas-vaadin` → projeto `vaadin6`
     - `geovendas-vaadin24` ou `geovendas-vaadin23` ou `ibtech-geovendas` → projeto `vaadin24`
     - `pedidos` ou `geovendas-isf` → projeto `pedidos`

2. Se encontrou PRs, analisar os diffs:
   - Usar `gh pr diff <PR_URL>` para ver mudancas
   - Listar arquivos alterados
   - Identificar: telas (views/controllers), endpoints (REST/resources), entidades (models/entities)
   - Mapear o que mudou para fluxos testaveis

3. Se NAO encontrou PRs na tarefa:
   - Perguntar ao QA: "Nao encontrei PRs vinculadas a QUA-XXXX. Pode me passar os links das Pull Requests?"

Sem tarefa Jira (modo livre):
- Perguntar: "Qual sistema vamos testar? (IGS/Vaadin 6, CRM360/Vaadin 24, ou Pedidos/ISF)"
- Perguntar: "Descreva o que precisa ser testado"

---

## FASE 2: Entrevista do QA

### Regras da Entrevista

- **UMA pergunta por vez** — nunca bombardear com multiplas perguntas
- **Nunca aceitar respostas vagas** — se o QA diz "testar a tela de pedidos", perguntar "Qual fluxo especifico? Criacao? Edicao? Consulta? Finalizacao?"
- **Sempre pedir exemplos concretos** — "Me de um exemplo de dado que voce usaria nesse teste"
- **Apos cada resposta, perguntar "E se...?"** — explorar edge cases
- **Preferir multipla escolha** quando possivel
- **Nao parar ate o QA confirmar** que nao tem mais cenarios
- **Se o QA for vago**, reformular a pergunta com opcoes concretas baseadas na analise das PRs

### Roteiro de Perguntas

Apresentar primeiro o que voce entendeu das PRs, depois perguntar:

1. **Confirmacao de escopo** (se veio do Jira):
   "Analisei as PRs e identifiquei que foram alterados: [lista de arquivos/funcoes]. Confirma que esses sao os fluxos que preciso testar?"

2. **Telas afetadas**:
   "Quais telas especificas eu preciso acessar para testar isso? Me descreva o caminho de navegacao (ex: menu > submenu > tela)."

3. **Cenarios de sucesso (happy path)**:
   "Descreva passo a passo o que um usuario faria nessa tela para o cenario funcionar corretamente. Quais campos preenche? Quais botoes clica? O que espera ver?"

4. **Cenarios de erro**:
   "O que acontece se o usuario:
   - Deixar um campo obrigatorio vazio?
   - Colocar um valor invalido?
   - Nao tiver permissao?
   Qual mensagem de erro espera ver em cada caso?"

5. **Edge cases e historico de bugs**:
   "Tem algum cenario que ja deu bug antes nessa area? Alguma combinacao de dados que costuma dar problema?"

6. **Dados de teste**:
   "Quais dados preciso para executar esses testes? (clientes especificos, produtos, tabelas de preco, etc.) Esses dados ja existem no ambiente local?"

7. **Credenciais**:
   "Quais credenciais de acesso uso para testar? (usuario e senha do sistema)"
   IMPORTANTE: Salvar no arquivo `.env` em `~/repo/geo-codex/geo-qa/tests/.env`, NUNCA commitar credenciais.

8. **Validacoes especificas**:
   "Alem do que discutimos, tem alguma validacao especifica que preciso checar? (calculo, integracao com outro sistema, mensagem, redirect, email)"

9. **Testes de API**:
   "As PRs alteraram endpoints REST. Preciso testar a API diretamente tambem? Quais endpoints e quais respostas espera?"

10. **Confirmacao final**:
    "Entao vou gerar testes para: [resumo completo de todos os cenarios]. Tem mais algum cenario que esquecemos?"
    - So prosseguir quando o QA confirmar que esta completo

---

## FASE 3: Planejamento

Antes de gerar codigo, apresentar ao QA o plano de testes:

```
Vou gerar os seguintes testes para QUA-XXXX:

**Arquivo:** tests/[projeto]/features/QUA-XXXX-[descricao].spec.ts

**UI/E2E (@e2e):**
1. [descricao do teste e2e 1]
2. [descricao do teste e2e 2]
...

**API (@api):**
1. [descricao do teste api 1]
...

**Code-level (@code):**
1. [descricao do teste code 1]
...

Aprova este plano?
```

Esperar aprovacao explicita antes de gerar codigo.

---

## FASE 4: Geracao de Testes

### Convencoes

- Nome do arquivo: `QUA-XXXX-descricao-curta.spec.ts` (kebab-case, sem acentos)
- Usar `test.describe('QUA-XXXX: Descricao', () => { ... })` como wrapper
- Tags nos testes: `@e2e`, `@api`, `@code` para filtrar por nivel
- Importar fixtures de auth do projeto correspondente
- Screenshots automaticos em falha (ja configurado no playwright.config.ts)
- Testes devem ser independentes entre si — cada um faz seu proprio setup
- Usar `test.beforeEach` para login quando todos os testes precisam de autenticacao

### Antes de gerar, verificar reutilizacao

1. Verificar se ja existe teste para a mesma area:
   ```bash
   ls ~/repo/geo-codex/geo-qa/tests/[projeto]/features/
   ```
2. Se existir teste relacionado, ler o arquivo para entender o que ja esta coberto
3. Decidir: ATUALIZAR teste existente ou CRIAR novo
4. Se feature mudou (nova flag, novo campo, novo comportamento), atualizar o teste existente
5. Verificar fixtures existentes — se precisar de nova fixture, criar em `tests/[projeto]/fixtures/`

### Padrao de Teste — Nivel 1: UI/E2E (@e2e)

```typescript
import { test, expect } from '@playwright/test';
import { loginIGS } from '../fixtures/auth';

test.describe('QUA-XXXX: Descricao da Feature', () => {
  test.beforeEach(async ({ page }) => {
    await loginIGS(page);
  });

  test('deve [acao esperada no happy path] @e2e', async ({ page }) => {
    // Navegar ate a tela
    await page.goto('/rota-da-tela');

    // Interagir com elementos
    await page.getByRole('button', { name: 'Nome do Botao' }).click();
    await page.getByLabel('Nome do Campo').fill('valor');

    // Validar resultado
    await expect(page.getByText('Mensagem de sucesso')).toBeVisible();
  });

  test('deve mostrar erro quando [cenario de erro] @e2e', async ({ page }) => {
    await page.goto('/rota-da-tela');

    // Tentar acao invalida
    await page.getByRole('button', { name: 'Salvar' }).click();

    // Validar mensagem de erro
    await expect(page.getByText('Campo obrigatorio')).toBeVisible();
  });
});
```

### Padrao de Teste — Nivel 2: API (@api)

```typescript
import { test, expect } from '@playwright/test';

test.describe('QUA-XXXX: API - Descricao', () => {
  test('deve retornar dados corretos no GET @api', async ({ request }) => {
    const response = await request.get('/rest/endpoint');
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty('campo');
    expect(body.campo).toBe(valorEsperado);
  });

  test('deve criar recurso no POST @api', async ({ request }) => {
    const response = await request.post('/rest/endpoint', {
      data: { campo: 'valor' }
    });
    expect(response.status()).toBe(201);

    const body = await response.json();
    expect(body.id).toBeDefined();
  });

  test('deve rejeitar dados invalidos com 400 @api', async ({ request }) => {
    const response = await request.post('/rest/endpoint', {
      data: { campo: '' }
    });
    expect(response.status()).toBe(400);
  });
});
```

### Padrao de Teste — Nivel 3: Code-level (@code)

```typescript
import { test, expect } from '@playwright/test';

test.describe('QUA-XXXX: Logica - Descricao', () => {
  test('deve calcular [regra de negocio] corretamente @code', async () => {
    // Testar logica extraida das PRs
    // Para codigo TypeScript/JavaScript: importar e testar diretamente
    // Para codigo Java: validar via API ou reproduzir a logica
    const resultado = calcularDesconto(100, 10);
    expect(resultado).toBe(90);
  });
});
```

---

## Particularidades por Sistema

### Vaadin 6 (IGS) — `tests/vaadin6/`

- **Stack**: Java 8, Vaadin 6.8.19, GWT, Tomcat
- **URL**: `http://localhost:8080/IBTech_Geo/app`
- **Renderizacao**: Server-side via GWT — elementos tem classes CSS geradas (v-button, v-textfield, v-table)
- **Login**: Formulario Vaadin tradicional, pode estar dentro de iframe
- **Navegacao**: Hash fragments `/app#!nome-da-tela`
- **Seletores recomendados** (em ordem de preferencia):
  1. `getByRole('button', { name: 'Texto' })` — para botoes com texto visivel
  2. `getByText('Texto')` — para labels e mensagens
  3. `locator('.v-button-caption:has-text("Texto")')` — para botoes Vaadin
  4. `locator('.v-textfield')` — para inputs Vaadin
  5. XPath como ultimo recurso: `locator('//span[contains(text(),"Texto")]')`
- **Waits**: Sempre usar `waitForLoadState('networkidle')` apos acoes que disparam server roundtrip
- **Grids/Tabelas**: Componentes `v-table` — selecionar linhas via click, scroll pode ser necessario
- **REST API**: Endpoints em `/rest/` (Jersey JAX-RS)
- **Repos que mapeiam para este projeto**: `geovendas-vaadin6`, `geovendas-vaadin`

### Vaadin 24 (CRM360) — `tests/vaadin24/`

- **Stack**: Java 17, Vaadin 23.3.13, Spring Boot 2.7.1, Docker
- **URL**: `http://localhost:8081`
- **Renderizacao**: Vaadin Web Components (mais acessiveis que Vaadin 6) + React + Vue
- **Login**: JWT token via `GeoJwtService`, header `X-Api-Key`
- **Seletores recomendados** (em ordem de preferencia):
  1. `getByRole()` — funciona bem com Web Components
  2. `getByLabel()` — campos tem labels acessiveis
  3. `locator('vaadin-text-field')` — componentes Vaadin nativos
  4. `locator('vaadin-grid')` — grids nativos
- **REST API**: Endpoints em `/api/v1/` (Spring Controllers)
- **Swagger**: Disponivel em `/swagger-ui/` para referencia de endpoints
- **Para testes de API autenticados**:
  ```typescript
  // Extrair token apos login na UI
  const cookies = await page.context().cookies();
  // Ou usar endpoint de login direto (se disponivel em dev-mode)
  ```
- **Repos que mapeiam para este projeto**: `geovendas-vaadin24`, `geovendas-vaadin23`, `ibtech-geovendas`

### Pedidos (ISF / Forca de Vendas) — `tests/pedidos/`

- **Stack**: CoffeeScript, AngularJS 1.8.2, Grunt, Express.js, PouchDB
- **URL**: `http://localhost:9000`
- **Renderizacao**: SPA client-side (AngularJS), rotas com hash `/#/`
- **Login**: `/pages/signin`, credenciais criptografadas no localStorage
- **Navegacao**: Hash routes `/#/comercial/cadPedido`, `/#/cliente/conCliente`, etc.
- **Seletores recomendados** (em ordem de preferencia):
  1. `getByPlaceholder()` — muitos inputs usam placeholder
  2. `getByRole('button', { name: 'Texto' })` — para botoes
  3. `locator('[ng-model="campo"]')` — para campos Angular
  4. `locator('[ng-click="funcao()"]')` — para acoes Angular
  5. `locator('.form-control')` — Bootstrap classes
- **Selects customizados**: Podem precisar de `page.selectOption()` ou click em dropdown + click na opcao
- **Offline/Sync**: Testar sincronizacao eh critico — PouchDB armazena dados localmente
- **REST API**: Backend Express em `/pedido/`, `/cliente/`, `/prospect/`, `/utils/server`
- **Rotas principais**:
  - `/comercial/cadPedido` — criar pedido
  - `/comercial/conPedido` — consultar pedidos abertos
  - `/comercial/conPedidoFinalizados` — pedidos finalizados
  - `/cliente/cadCliente` — cadastrar cliente
  - `/cliente/conCliente` — consultar clientes
  - `/prospect/cadProspect` — cadastrar prospect
  - `/financeiro/conComissoes` — comissoes
  - `/configuracao/` — configuracoes e sincronizacao
- **Repos que mapeiam para este projeto**: `pedidos`, `geovendas-isf`

---

## FASE 5: Validacao e Commit

1. **Verificar que o teste compila:**
   ```bash
   cd ~/repo/geo-codex/geo-qa/tests
   npx playwright test --project=[projeto] --grep "QUA-XXXX" --list
   ```
   Se falhar, corrigir erros de TypeScript antes de prosseguir.

2. **Tentar executar (se ambiente disponivel):**
   Perguntar ao QA: "O sistema [nome] esta rodando localmente? Posso executar os testes agora para validar?"
   - Se sim: `npx playwright test --project=[projeto] --grep "QUA-XXXX" --headed` (headed para o QA ver)
   - Se nao: informar que o teste foi gerado mas precisa ser validado quando o ambiente estiver disponivel

3. **Mostrar resultado ao QA:**
   - Se passou: "Todos os X testes passaram! Vou commitar."
   - Se falhou: "O teste [nome] falhou com [erro]. Vou ajustar." → corrigir e re-executar
   - Se nao executou: "O teste foi gerado e esta pronto para execucao. Vou commitar."

4. **Salvar credenciais no .env (se ainda nao salvas):**
   Verificar se `~/repo/geo-codex/geo-qa/tests/.env` existe e tem as credenciais do QA.
   Se nao, criar a partir do `.env.example` e preencher com os dados fornecidos.

5. **Commit:**
   ```bash
   cd ~/repo/geo-codex
   git add geo-qa/tests/[projeto]/features/QUA-XXXX-*.spec.ts
   git add geo-qa/tests/[projeto]/fixtures/  # se criou/atualizou fixtures
   git commit -m "test(QUA-XXXX): [descricao do que foi testado]

   Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
   ```

6. **Push:**
   Perguntar ao QA: "Posso fazer push dos testes para o repositorio remoto?"

---

## Regras Gerais

- NUNCA commitar credenciais (`.env` esta no `.gitignore`)
- NUNCA gerar testes sem aprovacao do plano pelo QA
- NUNCA aceitar respostas vagas — sempre pedir detalhes
- SEMPRE verificar testes existentes antes de criar novos
- SEMPRE reutilizar fixtures quando possivel
- SEMPRE usar tags (@e2e, @api, @code) nos testes
- SEMPRE nomear arquivos no formato `QUA-XXXX-descricao.spec.ts`
- Se o QA mencionar um bug conhecido, criar teste especifico para esse cenario (teste de regressao)
- Se a PR alterou calculos ou regras de negocio, SEMPRE incluir testes @code
- Se a PR alterou endpoints REST, SEMPRE incluir testes @api
- Se a PR alterou telas/views, SEMPRE incluir testes @e2e
