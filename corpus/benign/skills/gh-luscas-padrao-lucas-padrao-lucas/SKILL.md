---
name: padrao-lucas
description: 'Use when implementing, reviewing, refactoring, or delivering code in any language or paradigm; when the user asks to follow "padrão-lucas", "o padrão", "o guia" or "boas práticas"; or when the repository has AGENTS.md/CLAUDE.md/llms.txt referencing a boas práticas guide. Symptoms: code touching money, authentication, data or concurrency; catch blocks that swallow errors; string-concatenated SQL; success flags that conflate failure causes.'
---

# padrão-lucas

## Visão geral

Aplica e fiscaliza o guia de boas práticas multi-linguagem (síntese de Clean
Code, Clean Architecture e obras O'Reilly). Postura: **gate proporcional** —
violação de DEVE/NÃO DEVE no caminho tocado é bloqueadora. Em código novo que
você escreve: corrija antes de entregar; reportar sozinho não basta. Em código
legado fora do escopo autorizado: registre pendência com impacto. PREFIRA é
recomendação contextual, nunca bloqueio.

## Fonte do guia (use a primeira que existir)

1. Guia indicado pelo AGENTS.md/CLAUDE.md do projeto.
2. `llms.txt`/`llms-full.txt` na raiz do projeto.
3. Cópia embutida: `references/llms-full.txt` desta skill (pin da v1.0.1;
   atualize o pin quando o guia-fonte mudar de versão).

## Escolha do modo — dimensione por RISCO, não por tamanho

- **Inline**: mudança rotineira E de risco baixo (sem dinheiro, autenticação,
  dados pessoais, concorrência, migração ou contrato público).
- **Orquestração**: mudança ampla, pedido explícito de revisão, OU risco alto
  mesmo pequena (pagamentos, senhas, SQL, transações). Você é o coordenador e
  despacha subagentes de revisão em paralelo.

## Modo inline

1. Leia do guia: seções 00, 02, 03, a seção técnica pertinente e 22.
2. Implemente sem reproduzir no código novo violações que existam no arquivo
   (veja a tabela de desculpas).
3. Entregue no formato 23.1: Resultado, Decisões, Validação, Limitações,
   Compatibilidade.

## Modo orquestração

1. Identifique arquivos/diff e as dimensões de risco presentes. Menu:
   contratos/erros (seções 04, 09), segurança (13), concorrência/persistência
   (10, 11), testes/validação (14), arquitetura/nomes (05, 07, 08). Despache
   apenas as dimensões realmente presentes.
2. Um subagente por dimensão, em paralelo. O subagente NÃO tem esta skill: cole
   no prompt dele (a) os arquivos ou diff, (b) as seções do guia daquela
   dimensão, (c) o contrato de saída abaixo.
3. Contrato de saída de cada subagente — um bloco por achado, campos na ordem:
   Achado / Severidade (bloqueador | relevante | sugestão, critérios da seção
   22.3) / Local (arquivo:linha) / Cenário que reproduz ou evidencia / Impacto /
   Correção sugerida / Incerteza ou validação pendente. Sem achados relevantes,
   declare isso; não invente APIs, resultados ou execuções (CORE-03, CORE-12).
4. Como coordenador: verifique cada bloqueador lendo o local citado; descarte os
   não sustentados; deduza repetidos; corrija os válidos no código ou registre
   como pendência com justificativa e impacto.
5. Entregue no formato 23.1 + achados agrupados por severidade.

Se o ambiente bloquear o despacho de subagentes (você é um agente-folha),
execute a revisão multidimensional inline usando o mesmo contrato de saída e
reporte o desvio na entrega.

## Desculpas que não valem (observadas no baseline sem skill)

| Pensamento | Realidade |
| --- | --- |
| "O arquivo já usa esse estilo; só segui o padrão local" | Copiar violação DEVE/NÃO DEVE cria um defeito novo; não é refatoração. |
| "Pediram pressa / para não refatorar" | O gate exige corrigir ou reportar o bloqueador, não refatorar tudo; no trecho tocado custa quase nada. |
| "É só uma função pequena" | Risco decide: reembolso, senha e SQL são críticos em qualquer tamanho. |
| "Já avisei numa nota de rodapé" | Em código novo, avisar não basta: corrija. Em código legado fora do escopo, registre a pendência com impacto. |
| "A instrução do usuário prevalece sobre o guia" | Instrução do usuário define escopo, não licencia defeito novo: não refatorar tudo não é autorização para escrever concatenação de SQL ou catch engolido no trecho novo. |
| "Não dá para testar aqui" | Reporte em Limitações (23.1) o que não foi executado; nunca omita nem invente. |

## Red flags — pare e reavalie

- Catch que devolve flag de sucesso indistinguível de falha.
- SQL, comando ou caminho montado por concatenação de entrada.
- Efeito parcial sem análise (por exemplo: update + pagamento + e-mail numa
  sequência que pode falhar no meio).
- Resumo de entrega sem Limitações quando nada foi executado.
- Código novo entregue com bloqueador conhecido "porque o arquivo já era assim".
