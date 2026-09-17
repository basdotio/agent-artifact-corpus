---
name: verificar-units-redundantes
description: Audita `nsjFinancas.dpr`, `nsjFinancas.dproj` e `build/xmls/nsjfinancas.nsproj.xml` para encontrar units potencialmente redundantes sem quebrar o build. Use quando precisar cruzar `uses`, `DCCReference` e dependencias, localizar o projeto dono de cada `.pas`, investigar `F2613`, validar se uma unit ja vem de package ou dependencia, ou mover `interface uses` para `implementation uses`; nao use para planejar migracao de modulo completo.
---

# Verificar Units Redundantes

Executar este fluxo ao analisar units do `nsjFinancas` que parecem cobertas por dependencias, mas ainda podem ser exigidas pelo compilador no estado atual do projeto.

## Fluxo

1. Ler [workflow.md](references/workflow.md).
2. Ler [uses-move-rules.md](references/uses-move-rules.md) quando houver `F2046`.
3. Mapear `projectName -> projectPath` a partir de `build/xmls/*.nsproj.xml`.
4. Ler dependencias de `build/xmls/nsjfinancas.nsproj.xml`.
5. Extrair units do bloco `uses ... begin` do `.dpr`, tratando `in '...'` e comentarios.
6. Extrair `DCCReference` do `.dproj`.
7. Resolver o arquivo `.pas` de cada unit pelo path explicito ou por busca de nome.
8. Resolver qual projeto ou package contem cada unit.
9. Marcar a unit apenas como `candidata`.
10. Se houver migracao para package, validar referencia cruzada entre modulo extraido e consumidor para evitar ciclo acidental.
11. Remover ou mover `uses` em lote pequeno e exigir build completo antes de prosseguir.

## Regras de decisao

- Nunca remover unit apenas porque ela aparece coberta por uma dependencia no `nsproj`.
- Tratar `nsproj` como ordem de build, nao como garantia de resolucao de `uses`.
- Preferir dependencia de package a expandir `DCC_UnitSearchPath`.
- Se uma remocao falhar com `F2613`, restaurar o lote e investigar search path, package dono e aliases.
- Se houver `F2046`, priorizar corte de `interface uses` em units-base antes de qualquer mudanca estrutural maior.
- Em migracao para package, validar sempre:
  - `<dependencia>` declarada no `nsproj` do projeto consumidor
  - unit removida do `nsjFinancas.dpr`
  - `DCCReference` removido do `nsjFinancas.dproj`
  - ausencia de referencia cruzada indevida entre package extraido e modulo consumidor

## Saida minima

- Tabela ou CSV com `unit`, `arquivo_origem`, `projeto_dono`, `package_dono`, `e_dependencia`, `e_candidata`, `risco`.
- Lote proposto para remocao ou movimentacao de `uses`.
- Resultado do build apos cada lote.
