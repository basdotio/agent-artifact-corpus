---
name: avoid-overengineering
description: Use quando o usuário quiser implementar ou refatorar uma feature em um repositório Next.js e houver risco de antecipar complexidade, criar abstrações sem necessidade atual, ou planejar mais do que executar. Esta skill reduz o escopo para o menor slice útil, separa responsabilidades com MVC simples, preserva regras de negócio fora da infraestrutura e evita camadas genéricas sem caso concreto. Não use para tarefas puramente visuais, texto, ou quando o usuário explicitamente pedir uma arquitetura ampla e futura.
---

# Avoid Overengineering

## 1. Fundamento conceitual antes da implementação

Overengineering, aqui, significa adicionar complexidade interna antes de existir demanda concreta para ela.

O princípio base é:

- complexidade externa já vai entrar naturalmente no sistema
- portanto, não antecipe complexidade interna por medo ou ansiedade do futuro
- prefira fazer da forma mais simples possível agora
- evolua de forma orgânica, um passo concreto por vez
- preserve código fácil de ler, modificar e reutilizar

Regra principal:

> Resolva o problema atual inteiro, mas não resolva problemas futuros hipotéticos.

Outra regra principal:

> Se o comportamento público cabe em menos peças, use menos peças.

## 2. Separação clara de responsabilidades

Use a divisão abaixo para decidir onde cada coisa começa e termina.

| Componente | Responsabilidade | Não deve fazer |
|---|---|---|
| rota / entrypoint | receber a chamada do framework | regra de negócio, SQL, validação complexa |
| controller | traduzir request em chamada de negócio e traduzir saída em response | conhecer detalhes de conexão, persistência ou infraestrutura |
| model | executar regra de negócio e operações concretas do domínio | depender de `request`, `response` ou detalhes do framework |
| infraestrutura | transportar informação para banco, fila, serviço externo ou filesystem | decidir regra de negócio |
| migration | alterar estrutura persistida quando o shape dos dados mudou | encapsular regra de negócio |
| teste | provar comportamento público e integração entre peças | duplicar implementação |

Limites práticos:

- o controller começa no ponto em que entram detalhes de protocolo ou framework
- o model começa no ponto em que o sistema computa, valida, decide ou transforma algo relevante
- infraestrutura só leva e traz informação
- se uma peça só existe "para um dia talvez", ela ainda não deveria existir

## 3. Padrões abstratos antes de implementações concretas

Antes de escrever código, defina este contrato mínimo:

### Entrada
- qual comportamento público precisa existir agora
- qual dado entra
- qual saída observável precisa ser devolvida
- qual erro observável precisa existir

### Saída
- menor conjunto de arquivos necessário
- menor fluxo completo necessário
- critério observável de pronto

### Fluxo padrão
1. congelar o escopo em **um** comportamento público
2. escrever ou ajustar **um** teste desse comportamento
3. implementar o mínimo no controller
4. extrair model somente quando houver lógica concreta de negócio
5. tocar em infraestrutura somente se a feature realmente precisar
6. parar quando o comportamento estiver pronto

### Regras de decisão

Crie **somente** o que for necessário agora.

Adicione um novo model quando:
- existe regra de negócio concreta
- ou a mesma lógica precisa ser reutilizada
- ou o controller começou a computar demais

Adicione middleware quando:
- a mesma preocupação transversal já apareceu mais de uma vez

Adicione migration quando:
- a estrutura persistida realmente precisa mudar

Não adicione por padrão:
- service layer
- repository layer
- factory
- adapter
- provider system
- plugin system
- engine genérica
- multi-tenant abstraction
- suporte a múltiplos bancos
- suporte a múltiplos provedores
- config system amplo
- feature flags
- DTOs separados
- mapeadores extras

Só adicione qualquer item acima se o problema **atual** exigir diretamente.

## 4. Exemplos agnósticos de biblioteca

### Contrato mínimo entre controller e model

```js
// EXEMPLO DE USO
// controller: recebe detalhes do framework e chama o domínio
async function controller(input) {
  const output = await modelAction(input)
  return {
    statusCode: 200,
    body: output,
  }
}

// EXEMPLO DE USO
// model: recebe dados simples, decide, valida e executa o comportamento
async function modelAction(input) {
  return {
    ok: true,
    value: input.value,
  }
}
```
