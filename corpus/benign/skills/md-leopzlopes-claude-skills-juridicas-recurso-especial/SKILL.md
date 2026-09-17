---
name: recurso-especial
description: |
  Elabora minutas, contrarrazões e peças recursais para tribunais superiores (STJ e STF)
  com validação obrigatória de admissibilidade, redação AI-friendly e humanização integrada.
  Cobre: REsp (art. 105 III CF), RE (art. 102 III CF), Contrarrazões ao REsp/RE,
  Agravo em REsp/RE (art. 1.042 CPC), Embargos de Divergência EREsp/ERE (art. 1.043 CPC),
  Agravo Interno STJ/STF (art. 1.021 CPC). Inclui: prequestionamento (explícito, implícito,
  ficto), óbices sumulares (Súmulas 5, 7, 83, 126, 203, 211, 283/STF, 284/STF, 320/STJ),
  cotejo analítico, divergência jurisprudencial, fungibilidade RE/REsp, Temas Repetitivos,
  repercussão geral, fundamentação vinculada, embargos prequestionadores, retratação no
  tribunal a quo, sobrestamento por repetitivo. Dispara mesmo sem o nome exato — basta
  contexto de violação a lei federal, divergência jurisprudencial entre tribunais, decisão
  monocrática de relator em tribunal superior, ou necessidade de levar causa ao STJ ou STF.
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Agent
  - AskUserQuestion
---

# Skill — Recursos nos Tribunais Superiores (unificada)

Esta skill produz minutas argumentativas de alta tecnicidade para recursos perante o STJ e o STF. O texto final é sempre prosa técnica corrida — parágrafos coesos, construção argumentativa progressiva, linguagem forense formal sem adjetivações desnecessárias. Todo output é **minuta a ser revisada pelo advogado responsável** antes do protocolo.

> **Aviso permanente**: Nunca invente súmulas, enunciados, Temas Repetitivos, acórdãos ou dispositivos legais. Cite apenas referências com alta confiança de existência e vigência. Quando houver dúvida, sinalize `[verificar no STJ/STF]` e prossiga. Todo conteúdo gerado é minuta sujeita à revisão do advogado.

---
## 1. Roteamento modular — arquivos de referência

A skill é modular. Quando os arquivos de referência estiverem disponíveis (em `references/`), leia **sempre** o arquivo da peça específica **e** `fundamentos-comuns.md`. Caso contrário, use o conteúdo dogmático embutido neste SKILL.md (seção 8).

| Peça | Arquivo de referência |
|---|---|
| REsp ou Contrarrazões ao REsp | `references/resp.md` |
| RE ou Contrarrazões ao RE | `references/resp.md` (seção "Recurso Extraordinário") |
| Agravo em REsp/RE (art. 1.042) | `references/agravo-resp-re.md` |
| Embargos de Divergência (art. 1.043) | `references/embargos-divergencia.md` |
| Agravo Interno STJ/STF (art. 1.021) | `references/agravo-interno.md` |
| Fundamentos, prequestionamento, súmulas | `references/fundamentos-comuns.md` (sempre) |

Se os arquivos `references/` não existirem no contexto atual (ex.: acionamento via plugin), utilizar diretamente as seções 8.1 a 8.3 deste SKILL.md como base dogmática.

---

## 2. Integração com outras skills

Esta skill aciona automaticamente outras skills quando necessário:

| Situação | Skill acionada | Quando |
|---|---|---|
| Recurso de 2ª instância (apelação, AI, EDcl cível) | `recursos-civel` | Se o recurso não for de tribunal superior |
| Humanização do texto final | `humanizer` | Obrigatório antes de entregar qualquer minuta |
| Memorial para o relator | `memorial-one-page` | Após distribuição, se solicitado |
| Geração do .docx final | `docx` (skill) | Na etapa de geração do documento |

**Regra de acionamento plugin vs. skill**: quando invocado via plugin `skills-escritorio:recurso-especial`, carregar este SKILL.md e seguir o mesmo fluxo. Quando invocado via skill do projeto (`recurso-especial`), seguir igualmente este fluxo — ambos convergem para a mesma lógica unificada.

---
## 3. Etapa 1 — Coleta de contexto obrigatória

Antes de qualquer rascunho, extraia do contexto ou pergunte ao advogado:

| Campo | Observação |
|---|---|
| **Tipo exato da peça** | REsp, RE, Contrarrazões, Agravo em REsp/RE, EDiv, Agravo Interno |
| **Polo** | Recorrente ou recorrido? |
| **Área material** | Cível, empresarial, consumerista, trabalhista, outra? |
| **Tribunal de origem** | TJ, TRF? (JECs → Súmula 203/STJ: não cabe REsp) |
| **Acórdão recorrido** | Data, resultado, relator, fundamentos principais |
| **Dispositivo federal/constitucional violado** | Artigo(s) e lei(s) exatos |
| **Alínea de cabimento** | "a", "b" ou "c" do art. 105 III CF (REsp) ou art. 102 III CF (RE) |
| **Prequestionamento** | Explícito? Implícito? Ficto (art. 1.025 CPC)? |
| **Tempestividade** | Data de intimação; houve EDcl? Feriados locais? |
| **Fundamentos autônomos** | O acórdão tem múltiplos fundamentos suficientes? (Súmula 283/STF) |
| **Preparo** | Valor recolhido / isento? |
| **Temas Repetitivos / Repercussão Geral** | Há tema vinculante favorável ou contrário? |

Se faltar informação essencial, faça uma pergunta objetiva antes de avançar.

---

## 4. Etapa 2 — Validação de admissibilidade (gate obrigatório)

**Esta etapa é obrigatória e precede qualquer redação.** O objetivo é eliminar hipóteses de inadmissibilidade antes de investir na minuta.

### 4.1 Diagnóstico visual

Apresente sempre antes do esqueleto:

```
DIAGNÓSTICO DE ADMISSIBILIDADE
─────────────────────────────────────────────────────
✅/⚠️/❌  1. Tempestividade (15 dias úteis — art. 1.003, §5º CPC)
✅/⚠️/❌  2. Preparo (art. 1.007 CPC)
✅/⚠️/❌  3. Regularidade de representação
✅/⚠️/❌  4. Decisão de TJ ou TRF — não JEC (Súmula 203/STJ)
✅/⚠️/❌  5. Prequestionamento [explícito/implícito/ficto]
✅/⚠️/❌  6. Cabimento constitucional — alínea(s) identificada(s)
✅/⚠️/❌  7. Fundamentação vinculada — enquadramento na alínea
✅/⚠️/❌  8. Matéria de direito — não reexame de provas (Súmulas 5 e 7/STJ)
✅/⚠️/❌  9. Todos os fundamentos autônomos impugnados (Súmula 283/STF)
✅/⚠️/❌ 10. Cotejo analítico (se alínea "c")
✅/⚠️/❌ 11. Repercussão geral demonstrada (se RE)
✅/⚠️/❌ 12. Ausência de Tema Repetitivo/Súmula contrária (Súmula 83/STJ)
─────────────────────────────────────────────────────
RISCO GLOBAL: BAIXO / MÉDIO / ALTO
Óbices prioritários: [listar]
```

### 4.2 Confronto sumular obrigatório

Verificar expressamente cada uma das 8 súmulas obstativas e declarar se incide ou não:

- **Súmula 5/STJ** — interpretação de cláusula contratual
- **Súmula 7/STJ** — reexame de prova
- **Súmula 83/STJ** — divergência superada
- **Súmula 126/STJ** — fundamento constitucional + infraconstitucional sem RE simultâneo
- **Súmula 203/STJ** — decisão de JEC
- **Súmula 211/STJ** — questão não apreciada apesar de EDcl
- **Súmula 283/STF** — fundamento autônomo não impugnado
- **Súmula 284/STF** — deficiência de fundamentação

### 4.3 Verificação de precedentes vinculantes

Verificar se há Tema Repetitivo, IAC, Súmula Vinculante ou Repercussão Geral que:
- **Favoreça** a tese → explicitar o alinhamento na peça
- **Contrarie** a tese → enfrentar frontalmente (distinguishing, superação, peculiaridades fáticas)
- **Esteja pendente** → avaliar sobrestamento (arts. 1.036-1.041 CPC)

### 4.4 Regra de bloqueio

- **Se RISCO ALTO**: alertar o advogado antes de prosseguir. Sugerir alternativas: EDcl prequestionadores, desistência fundamentada, interposição simultânea de RE/REsp, ou ajuste da tese.
- **Se RISCO MÉDIO**: prosseguir com ressalvas expressas no esqueleto.
- **Se RISCO BAIXO**: prosseguir normalmente.

---

## 5. Etapa 3 — Esqueleto para aprovação (formato AI-friendly)

### 5.1 Resumo executivo (obrigatório — 5 a 10 linhas)

Antes do esqueleto detalhado, apresentar um resumo executivo contendo:
- Qual é o problema jurídico central
- Qual dispositivo foi violado
- Qual precedente ampara a tese (se houver)
- Qual providência se pretende (reforma total/parcial, cassação, anulação)

Esse resumo será incorporado à peça final como abertura estratégica.

### 5.2 Estrutura de seções com títulos rastreáveis

O esqueleto usa títulos objetivos que facilitam tanto a leitura humana quanto o mapeamento por sistemas de triagem:

```
RECURSO ESPECIAL [ou outro tipo]

I.    ENDEREÇAMENTO
II.   QUALIFICAÇÃO DAS PARTES E DO PROCESSO
III.  RESUMO EXECUTIVO
IV.   DA TEMPESTIVIDADE
V.    DO CABIMENTO (art. 105, III, alínea [X], CF)
VI.   DO PREQUESTIONAMENTO
VII.  DOS PRESSUPOSTOS EXTRÍNSECOS DE ADMISSIBILIDADE
VIII. DAS RAZÕES DO RECURSO ESPECIAL
      8.1 Da violação ao art. [X] da Lei [Y]
          Tese: [enunciado padronizado em uma frase]
      8.2 Da violação ao art. [X] da Lei [Y] [se houver segundo fundamento]
          Tese: [enunciado padronizado]
      [8.3 Da divergência jurisprudencial — alínea "c" (se aplicável)]
IX.   DOS PEDIDOS
X.    [ASSINATURA]
```

### 5.3 Enunciado padronizado de tese

Para cada fundamento, formular a tese em formato verificável:

> **Tese:** É ilegal [conduta/interpretação] porque viola o art. [X] da Lei [Y], conforme Tema Repetitivo n.º [Z] do STJ / Súmula [N] / REsp n.º [paradigma].

Esse formato dialoga com ferramentas de extração de argumentos e facilita o mapeamento pelo gabinete.

Aguardar aprovação do advogado antes de avançar à redação.

---

## 6. Etapa 4 — Redação em prosa técnica humanizada

### 6.1 Regras de redação

1. **Tom**: preciso, formal, técnico-doutrinário; concisão argumentativa; sem retórica vazia
2. **Estrutura rígida**: seguir o esqueleto aprovado sem omitir seções
3. **Prequestionamento**: demonstrar sempre — explícito: citar página/trecho do acórdão; implícito: demonstrar que a questão foi decidida; ficto: citar EDcl + art. 1.025 CPC
4. **Súmulas**: citar número correto e texto quando relevante; nunca inventar
5. **Jurisprudência**: citar julgados do STJ/STF com dados completos (número, órgão julgador, relator, data, tese síntese). Preferir Temas Repetitivos, IACs, REsps paradigmáticos. Nunca transcrever longos trechos — extrair a tese e conectar ao caso concreto
6. **Cotejo analítico** (alínea "c"): transcrever trechos do acórdão recorrido e do paradigma; demonstrar similitude fática; não basta apontar divergência abstrata
7. **Fungibilidade**: se houver risco de confusão entre questão constitucional e infraconstitucional, invocar fungibilidade (arts. 1.032-1.033 CPC)
8. **Fundamentos autônomos**: impugnar TODOS; se algum fundamento for suficiente para manter o resultado, o recurso não prospera (Súmula 283/STF)

### 6.2 Estrutura AI-friendly dos blocos

Cada seção da peça deve funcionar como bloco rastreável:

**Sinalização expressa de requisitos** — escrever de forma quase "checkbox":
- "O recurso é tempestivo, pois interposto em [data], dentro do prazo de 15 dias úteis contados da publicação do acórdão em [data] (art. 1.003, §5º, CPC)."
- "O recurso é cabível nos termos do art. 105, III, alínea 'a', da CF, pois o acórdão recorrido contrariou o art. [X] da Lei [Y]."
- "Há prequestionamento explícito, pois o acórdão recorrido enfrentou a questão federal às fls. [X], nos seguintes termos: [transcrição breve]."

**Apresentação de precedentes de forma verificável:**
- Identificação: número do processo, órgão julgador, relator, data do julgamento
- Tese síntese: extrair em uma ou duas frases
- Conexão com o caso: demonstrar por que o precedente se aplica
- Quando disponível e conferido: link oficial

**Alinhamento consciente aos filtros de precedentes:**
- Se favorável: "A tese ora sustentada coincide com o Tema n.º [X] do STJ/STF, fixado em [data]."
- Se contrário: enfrentar frontalmente com distinguishing ou demonstração de superação

**Redução de ruído argumentativo:**
- Máximo 3 teses principais — as mais sólidas primeiro
- Sem digressões doutrinárias longas (aprofundar apenas se o advogado pedir)
- Dispositivos legais integrados ao raciocínio, não listados em bloco separado

### 6.3 Humanização obrigatória

Antes de entregar qualquer minuta, aplicar os princípios da skill `humanizer`. Verificar especialmente:

- **Não usar**: "resta evidenciado", "nesse diapasão", "cumpre mencionar", "importa destacar", "in casu" decorativo, "data venia" sem propósito, "mutatis mutandis" como enchimento
- **Não usar**: inflação de importância ("representa um marco", "consolida o papel"), gerundivas decorativas ("demonstrando", "evidenciando"), regra dos três forçada, hedging excessivo
- **Usar**: construções diretas, frases com comprimentos variados, detalhes específicos (folhas, datas, valores) no lugar de afirmações vagas
- **Manter consistência terminológica**: não alternar sinônimos para o mesmo conceito técnico (recorrente/apelante/insurgente)
- **Tom forense com presença**: ser direto sobre pontos fortes e fracos. Quando o argumento é bom, ir fundo. Quando há fragilidade, não disfarçar — sinalizar ao advogado

A auditoria final deve responder: "O que ainda torna esse texto obviamente gerado por IA?" — e corrigir.

---

## 7. Etapa 5 — Checklist final de admissibilidade AI-friendly

Antes de entregar a minuta, verificar cada item:

```
CHECKLIST FINAL — RECURSO PARA TRIBUNAL SUPERIOR
─────────────────────────────────────────────────────
[ ] 1.  Tipo de recurso identificado corretamente
[ ] 2.  Decisão atacada identificada (número, órgão, data, relator, dispositivo)
[ ] 3.  Tempestividade demonstrada com datas e cálculo
[ ] 4.  Cabimento fundamentado no dispositivo legal correto
[ ] 5.  Prequestionamento demonstrado (página do acórdão ou EDcl + art. 1.025)
[ ] 6.  Repercussão geral / transcendência demonstrada (se RE)
[ ] 7.  Violação de dispositivos apontada com precisão
[ ] 8.  Divergência jurisprudencial com cotejo analítico (se alínea "c")
[ ] 9.  Todos os fundamentos autônomos do acórdão impugnados
[ ] 10. Não incidência das Súmulas 5, 7, 83/STJ demonstrada
[ ] 11. Precedentes oficiais citados com dados completos e tese síntese
[ ] 12. Texto conciso, sem jurisprudência fantasma ou copiada acriticamente
[ ] 13. Humanização aplicada — nenhum padrão de IA remanescente
[ ] 14. Resumo executivo presente (5-10 linhas)
─────────────────────────────────────────────────────
```

---

## 8. Pressupostos críticos — referência rápida

### 8.1 Prequestionamento (art. 1.025 CPC)

- **Explícito**: artigo de lei federal citado expressamente no acórdão
- **Implícito**: questão decidida sem citar o artigo, mas abordando seu conteúdo
- **Ficto**: EDcl opostos para prequestionar, rejeitados; art. 1.025 CPC supre

### 8.2 Súmulas obstativas — quadro de referência rápida

| Súmula | Enunciado | Estratégia de contorno |
|---|---|---|
| **5/STJ** | Interpretação de cláusula contratual não enseja REsp | Demonstrar que a controvérsia é de direito (norma imperativa), não de hermenêutica contratual |
| **7/STJ** | Reexame de prova não enseja REsp | Aceitar fatos fixados pelo acórdão; demonstrar que a questão é de qualificação jurídica |
| **83/STJ** | Divergência superada pela jurisprudência do STJ | Demonstrar que a jurisprudência foi superada, está em revisão, ou o caso tem distinguishing |
| **126/STJ** | Fundamento constitucional + infraconstitucional sem RE | Interpor RE e REsp simultaneamente |
| **203/STJ** | Decisão de JEC não cabe REsp | Verificar se a decisão é de TJ/TRF, não de Turma Recursal |
| **211/STJ** | Questão não apreciada apesar de EDcl | Invocar prequestionamento ficto (art. 1.025 CPC) |
| **283/STF** | Fundamento autônomo não impugnado | Impugnar todos os fundamentos suficientes |
| **284/STF** | Deficiência de fundamentação | Enquadrar com precisão na alínea; demonstrar violação específica |

### 8.3 Alíneas de cabimento

**Art. 105, III, CF (REsp):**
- **Alínea "a"**: contrariar tratado ou lei federal, ou negar-lhes vigência
- **Alínea "b"**: julgar válido ato de governo local contestado em face de lei federal
- **Alínea "c"**: dar a lei federal interpretação divergente da que lhe haja atribuído outro tribunal

**Art. 102, III, CF (RE):**
- **Alínea "a"**: contrariar dispositivo da Constituição
- **Alínea "b"**: declarar inconstitucionalidade de tratado ou lei federal
- **Alínea "c"**: julgar válida lei ou ato de governo local contestado em face da CF
- **Alínea "d"**: julgar válida lei local contestada em face de lei federal

---

## 9. Template de referência — Recurso Especial

```
EXCELENTÍSSIMO SENHOR PRESIDENTE DO [TRIBUNAL DE ORIGEM]

Processo n.º [NÚMERO CNJ]
Recorrente: [NOME]
Recorrido: [NOME]

[RECORRENTE], [qualificação], por seus advogados que esta subscrevem, com fundamento
no art. 105, III, alínea(s) [a/b/c], da Constituição Federal, e nos arts. 1.029 e
seguintes do Código de Processo Civil, vem, tempestivamente, interpor

                              RECURSO ESPECIAL

em face do v. acórdão proferido pela [Câmara/Turma] deste Egrégio Tribunal, publicado
em [DATA], nos autos da [tipo de ação], pelas razões de fato e de direito a seguir
expostas.

Requer seja o presente recurso recebido e processado, com a remessa dos autos ao
Superior Tribunal de Justiça.

[Cidade]/[UF], [DATA].

[Nome do Advogado] | OAB/[UF] [NÚMERO]

---

COLENDO SUPERIOR TRIBUNAL DE JUSTIÇA

[I. RESUMO EXECUTIVO — 5 a 10 linhas]

[II. DA TEMPESTIVIDADE]

[III. DO CABIMENTO]

[IV. DO PREQUESTIONAMENTO]

[V. DOS PRESSUPOSTOS EXTRÍNSECOS]

[VI. DAS RAZÕES DO RECURSO ESPECIAL]
    [6.1 Da violação ao art. X da Lei Y]
    [6.2 Da violação ao art. X da Lei Y — segundo fundamento]
    [6.3 Da divergência jurisprudencial — alínea "c" (se aplicável)]

[VII. DOS PEDIDOS]

[Cidade]/[UF], [DATA].

Leopoldo Fernandes da Silva Lopes | OAB/MS 9.983
Daniel Schuindt Falqueiro | OAB/MS 10.678-B
```

---

## 10. Geração de documento com template LFA

Ao gerar qualquer documento final (.docx) — minuta de REsp, RE, Contrarrazões, Agravo em REsp, Embargos de Divergência, Agravo Interno — use o template oficial do escritório:

```python
from docx import Document
import glob, os

TEMPLATE = r"C:\Users\leopo\OneDrive - Lopes e Falqueiro Advogados\Documentos\Lopes e Falqueiro Advogados - MODELOS\Modelos de Peças e Documentos\LFA - Papel Timbrado.docx"

_dirs = glob.glob('/sessions/*/mnt/outputs')
OUTPUT_DIR = _dirs[0] if _dirs else '/mnt/outputs'

doc = Document(TEMPLATE)
for p in list(doc.paragraphs): p._element.getparent().remove(p._element)
for t in list(doc.tables):     t._element.getparent().remove(t._element)

# --- insira o conteúdo gerado aqui ---

doc.save(os.path.join(OUTPUT_DIR, "RecursoEspecial_[Caso]_[YYYY-MM-DD].docx"))
```

**Regras obrigatórias:**
- Abrir com `Document(TEMPLATE)` — preserva cabeçalho (logomarca LFA) e rodapé (contato) automaticamente
- Limpar parágrafos e tabelas do corpo antes de inserir conteúdo
- Usar `OUTPUT_DIR` dinâmico via glob (nunca hardcode session ID)
- Prefixo sugerido: `RecursoEspecial_`, `Contrarrazoes_REsp_`, `AgravoREsp_`, `EmbargosDiv_`, `AgravoInterno_`

---

## 11. Lembrete permanente

- **Nunca inventar** dispositivos legais, súmulas, Temas Repetitivos, acórdãos ou ementas. Se não houver certeza, indicar `[verificar no STJ/STF]`.
- **Todo output é minuta** — nunca protocolar sem revisão manual do advogado.
- **Rotina mínima**: (a) gerar rascunho; (b) revisão jurídica pelo advogado; (c) validar fatos, datas e jurisprudência; (d) ajustar linguagem ao caso concreto.
- **Precedentes**: checar cada precedente citado em fonte oficial antes de incluir. Tribunais estão atentos a uso indevido de IA e à litigância abusiva.
- **Prequestionamento**: sem ele, o recurso não é conhecido. Verificar antes de redigir.
- **Honorários recursais** (art. 85, §11, CPC): majoração automática em caso de desprovimento — considerar na avaliação estratégica.
- **Humanização**: a peça deve soar como escrita por advogado experiente, não por ferramenta de IA. Aplicar os 31 padrões do humanizer como filtro final.
