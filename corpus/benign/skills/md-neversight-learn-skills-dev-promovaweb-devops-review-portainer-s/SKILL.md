---
name: promovaweb-devops-review-portainer-stack
description: Verifica a Stack do Portainer. Além disso analisa parâmetros, rotas Traefik, volumes, recursos e conformidade do stack Portainer de Acordo com as Recomendações da Promovaweb.
license: MIT
metadata:
  author: promovaweb
  version: "1.1"
---

# Review Portainer Stack

Executa uma auditoria completa do arquivo `portainer.yaml` e reporta conformidade, problemas e sugestões.

## Instruções de Execução

Quando esta skill for invocada, siga **exatamente** este roteiro:

### Passo 1 — Ler o arquivo

Leia o arquivo `portainer.yaml` completo.

### Passo 2 — Executar todos os checks abaixo

Execute cada bloco de verificação e registre os resultados (✅ OK / ⚠️ Atenção / ❌ Erro).

### Passo 3 — Gravar o resultado

Grave o relatório completo em um arquivo chamado portainer.audit.md.

---

## Checks de Verificação

### 1. Imagens

Verifique as imagens dos serviços:

**Agent:**

- Deve usar `portainer/agent:sts` ou versão estável (`portainer/agent:<versão>`)
- Alertar se estiver usando tag instável em produção

**Portainer CE:**

- Deve usar `portainer/portainer-ce:sts` ou versão estável
- Verificar se a tag `sts` (Short Term Support) é adequada ou se `lts` (Long Term Support) é mais apropriado para produção

---

### 2. Serviços Obrigatórios

Verifique se todos estes serviços estão presentes:

| Serviço | Obrigatório |
|---|---|
| `agent` | Sim |
| `portainer` | Sim |

---

### 3. Comando do Portainer

Verifique o comando do serviço `portainer`:

- Deve conter `-H tcp://tasks.agent:9001` — aponta para o serviço agent via DNS do Swarm
- Deve conter `--tlsskipverify` — permite comunicação sem TLS entre portainer e agent (aceitável em rede interna)
- Alertar se a URL do agent não usar `tasks.agent` (nome de serviço do Swarm)

---

### 4. Modo de Deploy

**Agent:**

- Deve usar `mode: global` — garante que um agent roda em cada nó do Swarm
- Alertar se não for `global` (agents ausentes em alguns nós)

**Portainer:**

- Deve usar `mode: replicated` com `replicas: 1`
- Alertar se tiver mais de 1 réplica (Portainer CE não suporta HA nativo)

---

### 5. Placement Constraints

**Agent:**

- Deve ter `node.platform.os == linux` — garante compatibilidade com nós Linux
- Não deve ter `node.role == manager` (agent deve rodar em todos os nós)

**Portainer:**

- Deve ter `node.role == manager` — interface web acessível apenas no manager

---

### 6. Volumes do Agent

**Agent:**

- `/var/run/docker.sock:/var/run/docker.sock` — obrigatório para comunicação com Docker
- `/var/lib/docker/volumes:/var/lib/docker/volumes` — obrigatório para gerenciamento de volumes

Alertar se algum desses volumes estiver ausente no agent.

---

### 7. Volume do Portainer

- `portainer_data` — deve ser declarado como `external: true`
- Verificar se está montado em `/data`
- Alertar se o volume não for externo (dados de configuração perdidos em redeploy)

---

### 8. Portas Expostas

**Portainer:**

- `9000:9000` — porta HTTP do Portainer
- Verificar se esta porta é necessária ou se apenas Traefik (HTTPS) é suficiente
- Alertar se porta 9000 exposta e Traefik também configurado (redundante)

**Agent:**

- Não deve ter portas expostas publicamente (comunicação apenas interna via Swarm)

---

### 9. Rotas Traefik

Para o serviço `portainer`, verifique:

**Âncora de endereço (`x-portainer-app-url`):**

- A âncora `x-portainer-app-url` deve existir e conter um domínio válido (não placeholder como `painel.seudominio.com.br`)
- O domínio na âncora **deve ser idêntico** ao domínio dentro de `Host(...)` na label `traefik.http.routers.portainer.rule`
- Se não forem iguais, reportar como ❌ Erro: inconsistência entre `x-portainer-app-url` e a regra Traefik

**Labels obrigatórias:**

- `traefik.enable=true`
- `traefik.swarm.network=network_swarm_public`
- `traefik.http.routers.portainer.rule` — deve conter `Host(...)` com domínio válido e coincidir com `x-portainer-app-url`
- `traefik.http.routers.portainer.entrypoints=websecure`
- `traefik.http.routers.portainer.tls.certresolver=letsencryptresolver`
- `traefik.http.routers.portainer.service=portainer`
- `traefik.http.services.portainer.loadbalancer.server.port=9000`
- `traefik.http.routers.portainer.priority=1` — verificar se é adequado

**Regras:**

- O `agent` **não deve** ter labels Traefik (serviço interno)

---

### 10. Redes

**Agent:**

- Deve estar na rede `network_swarm_public`

**Portainer:**

- Deve estar na rede `network_swarm_public`
- A rede deve ser declarada como `external: true`

---

### 11. Segurança

- `--tlsskipverify` na comunicação portainer-agent — aceitável em rede interna, mas documentar
- Porta 9000 exposta + Traefik: considere remover a exposição de porta direta
- Portainer CE por padrão não tem autenticação além do login — garanta senha forte no primeiro acesso
- Verificar se o domínio configurado no Traefik tem acesso restrito (recomendado proteger com IP allowlist)

---

## Formato do Relatório de Saída

Ao final, produza um relatório estruturado:

```
# Relatório de Auditoria — portainer.yaml
Data: <data atual>

## Resumo
- Total de checks: X
- ✅ OK: X
- ⚠️ Atenções: X
- ❌ Erros: X

## Resultados por Categoria

### 1. Imagens
✅ portainer/agent:sts: tag definida
⚠️ Tag `sts` (Short Term Support): considere `lts` para ambientes de produção estáveis
...

### 2. Serviços
✅ agent: presente
✅ portainer: presente

### 3. Comando
✅ portainer: -H tcp://tasks.agent:9001 --tlsskipverify correto
...

### 4. Modo de Deploy
✅ agent: mode global (correto para todos os nós)
✅ portainer: mode replicated, 1 réplica
...

### 5. Placement
✅ agent: node.platform.os == linux
✅ portainer: node.role == manager
...

### 6. Volumes Agent
✅ docker.sock: montado
✅ docker volumes: montado
...

### 7. Volume Portainer
✅ portainer_data: volume externo em /data
...

### 8. Portas
⚠️ Porta 9000 exposta e Traefik configurado — considere remover exposição direta de porta
...

### 9. Rotas Traefik
✅ portainer: rota Host correta, TLS ok
✅ agent: sem Traefik (correto)
...

### 10. Redes
✅ network_swarm_public: configurado como external
...

### 11. Segurança
⚠️ --tlsskipverify: documentar que comunicação interna é confiável
⚠️ Configure senha forte no primeiro acesso ao Portainer
⚠️ Considere adicionar IP allowlist no Traefik para o Portainer
...

## Ações Recomendadas (por prioridade)

### Crítico (fazer antes do deploy)
1. ...

### Recomendado
1. ...

### Opcional
1. ...
```
