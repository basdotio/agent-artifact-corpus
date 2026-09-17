---
name: tradipar-core-api-dev
description: Habilidade para o novo framework set-and-forget Node.js/TypeScript (Tradipar Core API), focando em OAuth2 Sankhya M2M e integração Real-Time via Webhooks.
---

# Tradipar Core API Dev (Enterprise Framework)

Você atua na camada da nova **Enterprise Core API** (`tradipar-core-api/`). Este é o ecossistema sucessor do antigo `aws-server-alef`. É construído com princípios *Enterprise Grade*, tipagem forte (TypeScript), padrão MVC (Controllers/Services/Adapters) e arquitetura Event-Driven.

## Protocolos e Restrições Absolutas

1. **Autenticação Padrão M2M (Machine-to-Machine):**
   - **NUNCA** utilize o fluxo legado de `JSESSIONID` via `mge/service.sbr` com usuário e senha.
   - **SEMPRE** utilize o adaptador `sankhya.api.ts` que implementa o fluxo *OAuth 2.0 Client Credentials* usando `Client ID`, `Client Secret` e `X-Token`.
   - A geração do token Bearer deve ser injetada de forma invisível via interceptors do Axios (`sankhya.api.ts`) e cacheados em memória para reaproveitamento seguro antes do término do prazo de expiração (normalmente 300 segundos, atualizar 30s antes).
   - O endpoint de autenticação é de formato `URL Encoded form data` com `grant_type=client_credentials` em `/authenticate` (NÃO `/api/authenticate`).

2. **Arquitetura Modular (MVC / Separation of Concerns):**
   - **Adapters (`/adapters`):** Isolam o acesso ao mundo externo (Sankhya, HubSpot). Nenhuma regra de negócio deve residir nestes arquivos.
   - **Controllers (`/controllers`):** Recebem as requisições HTTP REST ou webhooks de outras aplicações. Validam o payload da entrada e delegam para a camada de Serviços. 
   - **Services (`/services`):** Onde reside a essência das regras de negócio. É a camada ideal para orquestrar dados de orçamentos, lidar com retentativas, e orquestrar múltiplos adapters.

3. **Event-Driven e Webhooks Nativos Sankhya:**
   - Para atualizações de status vindas do ERP Sankhya, **NÃO crie mecanismos de pooling (pesquisa contínua)**. 
   - Utilize webhooks passivos que aguardam disparos originados por extensões Java nativas do SDK Sankhya Om API do ERP (`@Service`). Isso muda a arquitetura de "Pull" para "Push Real-Time".

4. **Tratamento de Erros e Logs Resilientes:**
   - Faça logging claro de erros ressaltando a raiz do problema. A resposta de API falha muitas vezes com objetos profundos de erro (ex: `e.response?.data?.error?.descricao`). Não esconda esses detalhes cruciais nos logs.
   - A API não pode ter quedas drásticas (crashes irrecuperáveis). Capture erros na borda (Controllers) e garanta que chegue o status 500 elegante para o chamador, ao mesmo tempo que logue tudo no servidor.

5. **Engenharia de Tipos "Strict Mode":**
   - É inegociável manter o `tsconfig.json` em `"strict": true`. Tipagem rigorosa é fundamental.
   - Compile e passe a validação TypeScript perfeitamente usando (`npm run build`) para assegurar a construção da versão `dist/`.

6. **Protocolo de Anexos (PDF Attachment Engine):**
   - **Sankhya Upload:** Para `sessionUpload.mge`, utilize `sessionkey=ANEXO_SISTEMA_CabecalhoNota_${nunota}`, `fitem=S` e envie o `Content-Length` manualmente no cabeçalho do `formData`.
   - **HubSpot Sync:** O método `attachFileToHubspot` no `quoteService` deve ser usado para subir o base64 para o HubSpot Files API e criar a nota (Note) vinculada ao Deal.
   - **Workflow:** Geração de PDF no Sankhya -> Upload p/ Sankhya -> Upload p/ HubSpot -> Vínculo c/ Deal.
   - **Download de Arquivos HubSpot (CRITICO):**
     - **NUNCA** use `signed-url-redirect` (v2 FileManager API) para download programático — o 302 carrega auth headers pro CDN e retorna HTML.
     - **SEMPRE** use `GET /files/v3/files/{fileId}/signed-url` (v3 Files API) para obter a CDN URL como JSON.
     - Baixe o binário com `axios` puro (SEM `hubspotApi`): `axios.get(cdnUrl, { responseType: 'arraybuffer' })`.
     - No re-upload, inclua o `contentType` explícito no `formData.append` (ex: `image/png`, `application/pdf`).

7. **Workflow de Deploy (Continuous Delivery):**
   - **Compilação:** O Agente deve rodar `npm run build` localmente no WSL.
   - **Sincronização:** Use `rsync -avz --exclude 'node_modules' --exclude '.git' ./ user@host:~/...` para o servidor Oracle.
   - **Hot-Reload:** Graças aos Volumes no `docker-compose.yml`, o container lê o `dist/` sincronizado instantaneamente. Use `docker compose restart` ou `down/up` apenas se houver mudanças no `docker-compose.yml` ou `.env`.

## Endpoints de Vendas Pedidos (v1 EasyAPI)

### 1. Atualizar Pedido de Venda

A atualização de um Pedido de Venda já confirmado só é permitida se a TOP do pedido estiver configurada com a opção 'Permitir Alteração após Confirmar' ativada. Além disso, na alteração de pedido, sempre enviar os itens e os financeiros.
- **Versão mínima requerida**: Sankhya Om 4.34
- **Método**: `PUT /v1/vendas/pedidos/{codigoPedido}`

<details>
<summary>OpenAPI Definition</summary>

```json
{
  "openapi": "3.0.3",
  "info": {
    "title": "API Sankhya",
    "description": "API de Integrações com Gateway Sankhya.",
    "version": "1.0"
  },
  "paths": {
    "/v1/vendas/pedidos/{codigoPedido}": {
      "put": {
        "tags": ["Vendas Pedidos"],
        "summary": "Atualizar Pedido de Venda",
        "parameters": [
          {
            "name": "codigoPedido",
            "in": "path",
            "required": true,
            "schema": { "type": "integer", "format": "int64" }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": { "$ref": "#/components/schemas/atualizarPedido" }
            }
          }
        },
        "responses": {
          "200": { "description": "OK" }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "atualizarPedido": {
        "type": "object",
        "required": ["data", "financeiros", "hora", "itens", "serie", "valorTotal"],
        "properties": {
          "data": { "type": "string", "example": "30/05/2024" },
          "hora": { "type": "string", "example": "07:34" },
          "codigoVendedor": { "type": "integer", "example": 11 },
          "codigoCliente": { "type": "integer", "example": 8115 },
          "observacao": { "type": "string" },
          "valorTotal": { "type": "number", "example": 1060 },
          "itens": { "type": "array", "items": { "$ref": "#/components/schemas/Pedido_de_Vendasitem" } },
          "financeiros": { "type": "array", "items": { "$ref": "#/components/schemas/Pedido_de_Vendasfinanceiro" } }
        }
      },
      "Pedido_de_Vendasitem": {
        "type": "object",
        "required": ["codigoLocalEstoque", "codigoProduto", "controle", "quantidade", "sequencia", "valorUnitario"],
        "properties": {
          "sequencia": { "type": "integer" },
          "codigoProduto": { "type": "integer" },
          "quantidade": { "type": "number" },
          "valorUnitario": { "type": "number" },
          "codigoLocalEstoque": { "type": "integer" },
          "controle": { "type": "string" }
        }
      },
      "Pedido_de_Vendasfinanceiro": {
        "type": "object",
        "required": ["dataVencimento", "sequencia", "tipoPagamento", "valorParcela"],
        "properties": {
          "sequencia": { "type": "integer" },
          "tipoPagamento": { "type": "integer" },
          "dataVencimento": { "type": "string" },
          "valorParcela": { "type": "number" }
        }
      }
    }
  }
}
```
</details>

### 2. Cancela Pedido de Venda

Cancela um Pedido de Venda disponível no Sankhya Om. Obs.: Pedidos faturados não serão cancelados.
- **Versão mínima requerida**: Sankhya Om 4.34
- **Método**: `POST /v1/vendas/pedidos/{codigoPedido}/cancela`

<details>
<summary>OpenAPI Definition</summary>

```json
{
  "openapi": "3.0.3",
  "paths": {
    "/v1/vendas/pedidos/{codigoPedido}/cancela": {
      "post": {
        "summary": "Cancela Pedido de Venda",
        "parameters": [
          {
            "name": "codigoPedido",
            "in": "path",
            "required": true,
            "schema": { "type": "integer", "format": "int64" }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": { "motivo": { "type": "string", "example": "Cliente desistiu da compra" } }
              }
            }
          }
        },
        "responses": {
          "200": { "description": "OK" }
        }
      }
    }
  }
}
```
</details>

### 3. Consultar Pedidos de Venda

Consulta lista de pedidos com filtros de data, empresa, cliente, etc.
- **Método**: `GET /v1/vendas/pedidos`

<details>
<summary>OpenAPI Definition</summary>

```json
{
  "openapi": "3.0.3",
  "paths": {
    "/v1/vendas/pedidos": {
      "get": {
        "summary": "Consultar Pedidos de Venda",
        "parameters": [
          { "name": "page", "in": "query", "required": true, "schema": { "type": "integer" } },
          { "name": "codigoEmpresa", "in": "query", "required": true, "schema": { "type": "integer" } },
          { "name": "dataNegociacaoInicio", "in": "query", "schema": { "type": "string" } },
          { "name": "dataNegociacaoFinal", "in": "query", "schema": { "type": "string" } },
          { "name": "codigoCliente", "in": "query", "schema": { "type": "integer" } },
          { "name": "confirmada", "in": "query", "schema": { "type": "boolean" } }
        ],
        "responses": {
          "200": { "description": "OK" }
        }
      }
    }
  }
}
```
</details>

### 4. Incluir Pedido de Venda

Inclui um Pedido de Venda no Sankhya Om, SEMPRE A CONFIRMAR. Utiliza um `notaModelo` para preencher dados padrões (empresa, TOP, natureza).
- **Versão mínima requerida**: Sankhya Om 4.34
- **Método**: `POST /v1/vendas/pedidos`

<details>
<summary>OpenAPI Definition</summary>

```json
{
  "openapi": "3.0.3",
  "paths": {
    "/v1/vendas/pedidos": {
      "post": {
        "summary": "Incluir Pedido de Venda",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": { "$ref": "#/components/schemas/movimentoPedido" }
            }
          }
        },
        "responses": {
          "200": { "description": "OK" }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "movimentoPedido": {
        "type": "object",
        "required": ["notaModelo", "data", "hora", "itens", "financeiros", "valorTotal"],
        "properties": {
          "notaModelo": { "type": "integer", "description": "ID do Modelo de Nota configurado no Sankhya" },
          "data": { "type": "string", "example": "30/05/2024" },
          "hora": { "type": "string", "example": "07:34" },
          "codigoVendedor": { "type": "integer" },
          "codigoCliente": { "type": "integer" },
          "observacao": { "type": "string" },
          "valorTotal": { "type": "number" },
          "itens": { "type": "array", "items": { "$ref": "#/components/schemas/Pedido_de_Vendasitem" } },
          "financeiros": { "type": "array", "items": { "$ref": "#/components/schemas/Pedido_de_Vendasfinanceiro" } }
        }
      }
    }
  }
}
```
</details>

## Mindset do Agente
- *Construa de Forma Blindada*: Você está migrando uma herança complexa. A funcionalidade anterior tem manhas, mas a nova implementação devera sanar de forma definitiva as intermitências. Traga a lógica pro typescript apenas da forma que obedeça aos 7 pontos acima.

---
Co-Authored-By: Claude Sonnet 3.7 <noreply@anthropic.com>
