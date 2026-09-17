---
name: quality-gate
description: "Use esta skill depois de CODE_GREEN e REFACTOR para validar qualidade técnica não-segurança da mudança: testes relevantes, lint, typecheck, regressão funcional e aderência à SPEC. Ela produz um veredito claro antes de SECURITY_REVIEW, REPORT e COMMIT."
---

# Objetivo
Executar o gate de qualidade técnica do fluxo da feature.

## Leia antes de agir
1. `AGENTS.md`
2. `features/<feature>/SPEC.md`, se existir
3. `README.md`
4. `pyproject.toml`
5. scripts de check do repositório, se existirem
6. diff atual e testes afetados

## Use esta skill quando
- `CODE_GREEN` já tiver terminado
- a etapa `REFACTOR` já tiver concluído
- for hora de validar a mudança antes de segurança, report e commit

## Não use esta skill quando
- a SPEC ainda não estiver estável
- os testes RED ainda não estiverem escritos
- a implementação ainda não tiver chegado ao verde
- o objetivo principal for revisão de segurança

## Regras obrigatórias
- Valide apenas os checks relevantes para a mudança.
- Diferencie claramente:
  - check executado e aprovado
  - check executado e falhou
  - check não executado
- Não mascare lacunas de validação.
- Não transforme opinião estética em bloqueio falso.

## Estratégia
1. Mapear o escopo da mudança.
2. Selecionar checks relevantes.
3. Executar testes e validações adequadas.
4. Consolidar evidências.
5. Emitir veredito claro.

## Saída esperada
Use um destes estados:
- `QUALITY_PASS`
- `QUALITY_PASS_WITH_GAPS`
- `QUALITY_BLOCKED`

Inclua:
- checks executados
- resultado de cada check
- cobertura de risco observada
- lacunas restantes
- próximo passo recomendado
