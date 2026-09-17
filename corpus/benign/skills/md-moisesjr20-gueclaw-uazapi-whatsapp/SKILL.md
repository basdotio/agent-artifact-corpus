---
name: uazapi-whatsapp
framework: doe
description: Integração com a API UazAPI para WhatsApp. Use para enviar mensagens (texto, mídia), verificar status e gerenciar a instância WhatsApp do GueClaw. Requer UAIZAPI_TOKEN e UAIZAPI_BASE_URL.
---

# UazAPI WhatsApp Integration

> **Operação DOE** — Esta skill segue a arquitetura DOE. Toda execução obedece ao fluxo: **Análise → Plano → Aprovação → Execução → Review**. Quando um script falhar, aplique o loop de self-annealing: corrija, teste, atualize esta skill.

---

Skill para envio de mensagens e gerenciamento da instância WhatsApp via UazAPI.

## 🔑 Configuração desta Instância

```
Base URL: https://kyrius.uazapi.com   (variável UAIZAPI_BASE_URL)
Token:    ef81eb52-692d-4e31-b98e-c2c0d045013a  (variável UAIZAPI_TOKEN)
```

Leia os valores do ambiente — não hardcode. Use `api_request` com header `token: $UAIZAPI_TOKEN`.

## ⚠️ REGRAS ABSOLUTAS

1. **SEMPRE use a ferramenta `api_request`** para chamar a UazAPI. Não simule respostas.
2. Use a **base URL da variável `UAIZAPI_BASE_URL`**, não `api.uazapi.com`.
3. O header de autenticação é `token`, não `Authorization` nem `admintoken`.
4. O campo do número é `number` (não `phone`), o campo do texto é `text` (não `message`).

---

## 📤 Enviar Mensagem de Texto

**Endpoint:** `POST {UAIZAPI_BASE_URL}/send/text`

**Headers:**
```
Content-Type: application/json
token: {UAIZAPI_TOKEN}
```

**Body:**
```json
{
  "number": "5511999999999",
  "text": "Olá! 👋"
}
```

**Resposta de sucesso:**
```json
{
  "id": "3EB01466AB8EDCB02C6E54",
  "status": "Pending",
  "fromMe": true
}
```

---

## 📊 Verificar Status da Instância

**Endpoint:** `GET {UAIZAPI_BASE_URL}/instance/status`

**Headers:**
```
token: {UAIZAPI_TOKEN}
```

---

## 🖼️ Enviar Imagem

**Endpoint:** `POST {UAIZAPI_BASE_URL}/send/image`

**Body:**
```json
{
  "number": "5511999999999",
  "image": "https://url-da-imagem.jpg",
  "caption": "Legenda opcional"
}
```

---

## 🎵 Enviar Áudio

**Endpoint:** `POST {UAIZAPI_BASE_URL}/send/audio`

**Body:**
```json
{
  "number": "5511999999999",
  "audio": "https://url-do-audio.mp3"
}
```

---

## 📄 Enviar Documento

**Endpoint:** `POST {UAIZAPI_BASE_URL}/send/document`

**Body:**
```json
{
  "number": "5511999999999",
  "document": "https://url-do-arquivo.pdf",
  "fileName": "arquivo.pdf",
  "caption": "Legenda opcional"
}
```

---

## 📋 Formato do Número

- Sempre incluir DDI + DDD + número
- Sem espaços, traços ou parênteses
- Exemplos: `5511999999999`, `5585996701800`, `553171629814`

# UazAPI WhatsApp Integration

Skill para integração completa com a API UazAPI (WhatsApp).

## 🎯 O que é a UazAPI?

API de WhatsApp que permite:
- Criar e gerenciar instâncias do WhatsApp
- Enviar mensagens de texto, mídia e interativas
- Receber webhooks de mensagens
- Automatizar comunicação via WhatsApp

## 🔑 Variáveis de Ambiente

```bash
export UAIZAPI_TOKEN="seu_token_aqui"
export UAIZAPI_BASE_URL="https://api.uazapi.com"  # ou seu endpoint próprio
```

## 📚 Documentação Oficial

- **Docs:** https://docs.uazapi.com/
- **Postman:** https://www.postman.com/augustofcs/uazapi-v2
- **Versões:** v1.0 e v2.0

---

## 🚀 Endpoints Principais

### 1. Gerenciamento de Instâncias

#### Criar Instância
```bash
curl -X POST "https://api.uazapi.com/instance/init" \
  -H "Content-Type: application/json" \
  -H "admintoken: SEU_ADMIN_TOKEN" \
  -d '{
    "instanceName": "minha-instancia",
    "token": "token-personalizado-opcional"
  }'
```

#### Conectar (Gerar QR Code)
```bash
curl -X POST "https://api.uazapi.com/instance/connect" \
  -H "Content-Type: application/json" \
  -H "token: TOKEN_DA_INSTANCIA" \
  -d '{"phone": "5511999999999"}'  # Opcional: código de pareamento
```

#### Ver Status
```bash
curl -X GET "https://api.uazapi.com/instance/status" \
  -H "token: TOKEN_DA_INSTANCIA"
```

#### Desconectar
```bash
curl -X POST "https://api.uazapi.com/instance/disconnect" \
  -H "token: TOKEN_DA_INSTANCIA"
```

#### Listar Todas as Instâncias
```bash
curl -X GET "https://api.uazapi.com/instance/all" \
  -H "admintoken: SEU_ADMIN_TOKEN"
```

---

### 2. Envio de Mensagens

#### Enviar Texto
```bash
curl -X POST "https://api.uazapi.com/message/sendText" \
  -H "Content-Type: application/json" \
  -H "token: TOKEN_DA_INSTANCIA" \
  -d '{
    "phone": "5511999999999",
    "message": "Olá! 👋",
    "delay": 1000,
    "readchat": true
  }'
```

#### Enviar Imagem (por URL)
```bash
curl -X POST "https://api.uazapi.com/message/sendImage" \
  -H "Content-Type: application/json" \
  -H "token: TOKEN_DA_INSTANCIA" \
  -d '{
    "phone": "5511999999999",
    "image": "https://exemplo.com/imagem.jpg",
    "caption": "Descrição da imagem",
    "delay": 1000
  }'
```

#### Enviar Documento
```bash
curl -X POST "https://api.uazapi.com/message/sendDocument" \
  -H "Content-Type: application/json" \
  -H "token: TOKEN_DA_INSTANCIA" \
  -d '{
    "phone": "5511999999999",
    "document": "https://exemplo.com/arquivo.pdf",
    "fileName": "documento.pdf",
    "caption": "Veja este documento",
    "delay": 1000
  }'
```

#### Enviar Áudio
```bash
curl -X POST "https://api.uazapi.com/message/sendAudio" \
  -H "Content-Type: application/json" \
  -H "token: TOKEN_DA_INSTANCIA" \
  -d '{
    "phone": "5511999999999",
    "audio": "https://exemplo.com/audio.mp3",
    "delay": 1000
  }'
```

#### Enviar Menu/Botões (Interativo)
```bash
curl -X POST "https://api.uazapi.com/send/menu" \
  -H "Content-Type: application/json" \
  -H "token: TOKEN_DA_INSTANCIA" \
  -d '{
    "phone": "5511999999999",
    "message": "Escolha uma opção:",
    "type": "button",  # ou "list", "carousel", "poll"
    "buttons": [
      {"buttonId": "1", "buttonText": "Opção 1"},
      {"buttonId": "2", "buttonText": "Opção 2"}
    ]
  }'
```

---

## 🛠️ Scripts Disponíveis

### Python

```python
from scripts.uazapi_client import UazAPIClient

# Inicializar
client = UazAPIClient(
    base_url="https://api.uazapi.com",
    token="seu_token"
)

# Criar instância
instance = client.create_instance("minha-instancia")
print(f"Token da instância: {instance['token']}")

# Conectar (gerar QR)
qr = client.connect(instance['token'])
print(f"QR Code: {qr['qrcode']}")

# Enviar mensagem
client.send_text(
    instance_token=instance['token'],
    phone="5511999999999",
    message="Olá do FluxoHub! 👋"
)
```

### Bash/Curl

Ver `examples/curl_examples.sh`

---

## 📊 Fluxo Recomendado para FluxoHub

```
┌─────────────────┐
│  Workflow Node  │
│  (Trigger)      │
└────────┬────────┘
         ▼
┌─────────────────┐
│  Verificar      │
│  Status WhatsApp│
│  (UazAPI)       │
└────────┬────────┘
         ▼
┌─────────────────┐
│  Enviar         │
│  Notificação    │
│  (Texto/Mídia)  │
└────────┬────────┘
         ▼
┌─────────────────┐
│  Aguardar       │
│  Resposta       │
│  (Webhook)      │
└─────────────────┘
```

---

## ⚠️ Limitações e Considerações

1. **WhatsApp Business:** Recomendado usar contas Business para melhor estabilidade
2. **Delay padrão:** 5 segundos entre mensagens (configurável)
3. **Limite de vídeo:** 16MB (mesmo limite do WhatsApp Web)
4. **URLs:** Não devem conter caracteres especiais
5. **Concorrência:** `/sendList` e `/sendButton` podem não funcionar se o número estiver logado no WhatsApp Web

---

## 🔧 Troubleshooting

### Instância não conecta
- Verificar se QR code foi escaneado
- Verificar se número não está banido
- Tentar gerar novo QR code

### Mensagens não chegam
- Verificar se instância está `connected`
- Verificar formato do número (DDI + DDD + Número)
- Verificar delay entre mensagens

### Rate Limit
- Respeitar delay de 5s entre mensagens
- Usar filas para envio em massa

---

## 📁 Arquivos

- `scripts/uazapi_client.py` - Cliente Python completo
- `scripts/webhook_handler.py` - Handler para webhooks
- `examples/curl_examples.sh` - Exemplos com curl
- `examples/fluxohub_integration.md` - Guia de integração com FluxoHub
- `references/api_endpoints.md` - Lista completa de endpoints

---

## 📝 Exemplos de Uso no FluxoHub

### Node: Verificar Status
```javascript
const status = await fetch('https://api.uazapi.com/instance/status', {
  headers: { 'token': input.instanceToken }
});
return { output: await status.json() };
```

### Node: Enviar Mensagem
```javascript
const response = await fetch('https://api.uazapi.com/message/sendText', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'token': input.instanceToken
  },
  body: JSON.stringify({
    phone: input.phone,
    message: input.message,
    delay: 1000
  })
});
return { output: await response.json() };
```

---

## 💡 Dicas

1. **Sempre verifique o status** da instância antes de enviar mensagens
2. **Use delays** entre mensagens para evitar bloqueios
3. **Armazene os tokens** de instância de forma segura
4. **Monitore os webhooks** para receber respostas
5. **Tenha um plano B** (número alternativo) para contingência
