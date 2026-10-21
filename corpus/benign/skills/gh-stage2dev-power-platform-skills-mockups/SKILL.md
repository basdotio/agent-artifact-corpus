---
name: mockups
description: "Use quando a identidade visual do app Power Apps está aprovada e é hora da etapa 4 do pipeline: o Agente de Mockups em Imagem elenca todas as telas, a navegação, o loading, os erros e os estados vazios, e, com a autorização do usuário, o script gera uma imagem por tela pela API da OpenAI. Também refaz só as telas afetadas quando o protótipo voltou com ajuste. Não use antes do /pp:design, nem para desenhar uma tela em YAML (use `powerapps-canvas`)."
user-invocable: true
disable-model-invocation: true
---

# /pp:mockups — Agente de Mockups em Imagem

Etapa 4 do pipeline, bloco **2. Identidade e experiência**. O agente `pp:agente-mockups` monta o
inventário de telas e o spec das imagens; você confere, pede a autorização e gera as imagens.
Gerar imagem custa dinheiro e envia o texto das telas à OpenAI: **só com o "pode gerar" do usuário**.

`KIT` = `${CLAUDE_PLUGIN_ROOT}`. Formato de saída: `KIT/skills/power-platform/references/formato-saida.md`.
Script de estado: `python "${CLAUDE_PLUGIN_ROOT}/skills/power-platform/scripts/estado.py"`.
Modelos: `python "${CLAUDE_PLUGIN_ROOT}/skills/power-platform/scripts/modelos.py"`.
Script de imagens: `python "${CLAUDE_PLUGIN_ROOT}/skills/power-platform/scripts/desenhar-mockups.py"`.
Detalhe de chave, modelo e erros: `KIT/skills/power-platform/references/mockups.md`.

## Antes de começar

1. `estado.py comecar mockups`. Exit 1: mostre a saída e pare.
2. Confira que existem `docs/planejamento/prd.md` e `ux-design-system.md` com hex na seção 3.
3. **Modo:**
   - **novo**: não existe `docs/planejamento/mockups/mockups.json`;
   - **retomar**: o spec existe e o inventário já foi conferido (linha "Inventário conferido" no
     `inventario-telas.md`), mas faltam imagens (ex.: a sessão parou para definir a chave): vá
     direto ao passo 4;
   - **ajuste**: a etapa está *reaberta* e a rodada aberta de `ajustes-prototipo.md` tem itens
     `tela`. Sem itens `tela`, só confirme, vá ao portão e encerre com a nota "sem mudança de tela".

## Passos

1. **Agente.** Mostre `◆ Chamando o Agente de Mockups em Imagem...` e chame o subagente
   `pp:agente-mockups` (modelo: `modelos.py de agente-mockups`; linha vazia, não passe `model`) passando:
   - `RAIZ`: a raiz do projeto;
   - `KIT`: o valor de `${CLAUDE_PLUGIN_ROOT}`;
   - `MODO`: novo ou ajuste, e no ajuste os itens `tela` da rodada.
2. **Julgue a entrega** (`KIT/skills/power-platform/references/subagentes.md`, "Julgar a entrega"):
   - `desenhar-mockups.py docs/planejamento/mockups/mockups.json --simular` precisa terminar em
     `0 erro(s)` (o agente não roda scripts: a prova é sua);
   - todo `RF-xx` P0 do `prd.md` aparece em pelo menos uma tela da tabela;
   - a moldura segue a navegação da seção 2.1 do `ux-design-system.md`.
   Erro ou falta: revisão, com a saída do `--simular` ou o requisito sem tela. Registre com
   `estado.py veredito mockups --agente agente-mockups --resultado <...> --motivo "..."`.
3. **Conferência das telas** (checkpoint): mostre a tabela de telas que o agente devolveu (id, tela,
   perfis, prioridade) e a moldura em até 8 linhas. "Falta alguma tela ou estado? Digite 'aprovado'
   ou diga o que mudar." Mudança: chame o agente de novo com o pedido. Aprovado: grave
   "Inventário conferido: <data>" no `inventario-telas.md`.
4. **Decisão de gerar** (checkpoint, `AskUserQuestion`). Antes, leia no `brainstorm.md` a resposta
   sobre enviar a descrição das telas à OpenAI: se foi "não", pule para a opção 3 sem perguntar.
   Mostre a linha `# modelo · tamanho · qualidade` e o total de imagens do `--simular`:
   1. "Gerar as N imagens (Recomendado)";
   2. "Gerar só as telas P0 (M imagens)";
   3. "Não gerar: seguir para o protótipo sem imagens".
   Diga junto: custa por imagem (preço na página da OpenAI) e o texto das telas sai para a OpenAI,
   sem nenhum dado real.
5. **Chave.** Confira sem mostrar:
   `python -c "import os; print('definida' if os.environ.get('OPENAI_API_KEY') else 'ausente')"`.
   Ausente: checkpoint `Ação no ambiente` com o passo a passo de
   `KIT/skills/power-platform/references/mockups.md` §2 (`setx OPENAI_API_KEY "<sua-chave>"` no Windows, `export` no macOS/Linux). Diga
   que é preciso **fechar e abrir o Claude Code num terminal novo** e rodar `/pp:mockups` de novo:
   o trabalho feito até aqui fica no disco. Nunca peça a chave na conversa. Pare aqui.
6. **Gere:** `desenhar-mockups.py docs/planejamento/mockups/mockups.json` (só P0: `--telas` com os
   ids; ajuste: `--telas <ids> --sobrescrever`). Leia a última linha: `N erro(s)`. Erro `M101`:
   tabela da seção 6 do mesmo `mockups.md`.
7. **Conferência das imagens** (checkpoint): peça para abrir `docs/planejamento/mockups/mockups.md`.
   Imagem não é fonte de cor nem de medida: julgue estrutura e fluxo. Ajuste numa tela: edite o
   item no spec e gere só ela (`--telas <id> --sobrescrever`).

## Portão de saída

- [ ] `inventario-telas.md` com moldura, mapa de navegação e todas as telas P0, conferido pelo usuário.
- [ ] `--simular` com `0 erro(s)` (cole a última linha no resumo).
- [ ] Imagens geradas **ou** a decisão de não gerar registrada no inventário (quem decidiu, por quê, data).

## Encerrar

1. `estado.py concluir mockups --nota "<N> telas, <M> imagens"` (sem imagens: `"<N> telas; imagens
   dispensadas: <motivo>"`).
2. Commit se `git_commit_por_etapa`: `pp(mockups): inventário de telas e mockups`. As imagens entram
   no commit; a chave nunca.
3. Resumo e o bloco "Próximo passo" que o script imprimiu.
