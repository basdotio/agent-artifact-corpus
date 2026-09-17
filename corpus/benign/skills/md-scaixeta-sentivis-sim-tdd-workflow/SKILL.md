---
name: tdd-workflow
description: Fluxo RED-GREEN-REFACTOR aplicado aos projetos MCP com disciplina de escopo, rastreabilidade e conformidade DOC2.5.
---
# TDD Workflow

## Quando usar
Usar para implementar comportamento novo com segurança, priorizando prevenção de regressão.

## Procedimento
1) RED: escrever teste que falha para o requisito.
2) GREEN: implementar mínimo para passar.
3) REFACTOR: limpar design sem quebrar teste.
4) Repetir ciclo até atender critérios de aceite.

## Restrições DOC2.5
- Não pular fase RED.
- Não refatorar fora do escopo pedido.
- Não propor commit sem comando do PO.

## Dependências
- Suite de testes operacional
- Critérios de aceite explícitos
