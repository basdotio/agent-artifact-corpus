---
name: split
description: "Dividir e separar imagens em múltiplas partes independentes. Use esta skill sempre que o usuário pedir para dividir imagem em grade/grid, separar elementos de uma imagem, extrair ícones de sprite sheet, cortar imagem em pedaços, fatiar em colunas ou linhas, auto-detectar elementos em fundo uniforme, separar imagens compostas. Também ativa para 'split', 'grid', 'sprite sheet', 'separar elementos', 'dividir em partes', 'extrair de imagem', 'desmembrar', 'fatiar', 'split horizontal', 'split vertical', 'auto-split', 'detectar elementos', 'collage para imagens individuais'. Inclui detecção automática de elementos com OpenCV."
---

# Image Split

Ferramenta para dividir imagens em múltiplas partes independentes: grade regular, faixas horizontais/verticais, e auto-detecção de elementos em fundo uniforme.

Usa Pillow + numpy + OpenCV (headless) em virtualenv isolado em `~/venvs/image-split/`.

## Setup

### Verificar se já está instalado

```bash
test -f ~/venvs/image-split/bin/python && ~/venvs/image-split/bin/python -c "import PIL; import numpy; print('OK')" || echo "PRECISA_INSTALAR"
```

### Instalar (se necessário)

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/split/scripts/setup.sh
```

## Uso

```bash
~/venvs/image-split/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/split/scripts/split.py INPUT --OPERAÇÃO [OPÇÕES]
```

Cada operação gera múltiplos arquivos em uma pasta de saída. Por padrão cria `<nome>_split/` ao lado do arquivo original.

---

## Referência rápida

| Operação | Flag | Exemplo | Resultado |
|----------|------|---------|-----------|
| Grade | `--grid CxR` | `--grid 4x3` | 12 pedaços (4 col × 3 linhas) |
| Faixas horiz. | `--split-h N` | `--split-h 3` | 3 faixas de cima para baixo |
| Faixas vert. | `--split-v N` | `--split-v 2` | 2 faixas esquerda para direita |
| Auto-detect | `--auto-split` | `--auto-split` | N elementos detectados |

---

## Grid (grade regular)

`--grid CxR` divide a imagem em C colunas × R linhas.

```bash
# Sprite sheet 4 colunas × 3 linhas = 12 sprites
~/venvs/image-split/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/split/scripts/split.py sprites.png --grid 4x3

# Collage 2×2
~/venvs/image-split/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/split/scripts/split.py collage.jpg --grid 2x2
```

Arquivos de saída seguem o padrão: `{nome}_r{linha}_c{coluna}.{ext}`

---

## Split horizontal

`--split-h N` divide em N faixas horizontais iguais (cortes de cima para baixo).

```bash
# Banner longo → 3 partes iguais
~/venvs/image-split/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/split/scripts/split.py banner.jpg --split-h 3
```

Arquivos de saída: `{nome}_strip_{n}.{ext}`

---

## Split vertical

`--split-v N` divide em N faixas verticais iguais (cortes da esquerda para direita).

```bash
# Panorâmica → 2 metades
~/venvs/image-split/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/split/scripts/split.py panorama.jpg --split-v 2
```

Arquivos de saída: `{nome}_col_{n}.{ext}`

---

## Auto-split (detecção de elementos)

`--auto-split` detecta elementos distintos em fundo uniforme e extrai cada um como imagem independente. Ideal para:
- Sprite sheets com espaçamento irregular
- Coleções de ícones/logos em fundo branco
- Screenshots com múltiplos elementos
- Collages onde cada item tem tamanho diferente

**Método de detecção:** Usa OpenCV (contour detection com operações morfológicas) se disponível. Fallback para análise de projeção com numpy — funciona bem para layouts organizados em grade/coluna/linha.

```bash
# Auto-detectar elementos
~/venvs/image-split/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/split/scripts/split.py icons.png --auto-split

# Elementos pequenos (mínimo 30px)
~/venvs/image-split/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/split/scripts/split.py stickers.png --auto-split --min-size 30

# Mais margem ao redor de cada elemento
~/venvs/image-split/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/split/scripts/split.py composicao.png --auto-split --split-padding 15

# Fundo não-uniforme (aumentar tolerância)
~/venvs/image-split/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/split/scripts/split.py foto.jpg --auto-split --fuzz 50
```

### Parâmetros de auto-split

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| `--min-size N` | 50 | Tamanho mínimo em pixels para considerar como elemento |
| `--split-padding N` | 5 | Margem ao redor de cada elemento extraído |
| `--fuzz N` | 30 | Tolerância para detecção de fundo (0-255) |

**Dicas para ajustar:**
- Se detecta muitos elementos pequenos/ruído: aumentar `--min-size`
- Se corta elementos nas bordas: aumentar `--split-padding`
- Se não detecta elementos (tudo vira fundo): diminuir `--fuzz`
- Se fundo é incluído como elemento: aumentar `--fuzz`

---

## Opções de saída

| Opção | Descrição |
|-------|-----------|
| `--output DIR` | Diretório de saída (padrão: `<nome>_split/` ao lado do original) |
| `--prefix TEXTO` | Prefixo para nomes dos arquivos (padrão: nome do arquivo original) |
| `--format EXT` | Formato de saída: jpg, png, webp, bmp, tiff (padrão: mesmo do original) |
| `--quality N` | Qualidade JPG/WebP (1-95, padrão: 85) |

```bash
# Salvar como WebP em pasta específica
~/venvs/image-split/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/split/scripts/split.py sprite.png --grid 4x4 --format webp --output ~/sprites/

# Prefixo customizado
~/venvs/image-split/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/split/scripts/split.py tileset.png --grid 8x8 --prefix tile
```

---

## Manifesto

Cada operação de split gera um `_manifest.json` no diretório de saída com metadados: arquivo fonte, operação, e lista de pedaços com dimensões. Útil para automação e referência.

---

## Fluxo de trabalho

1. Verificar se `~/venvs/image-split/bin/python` existe
2. Se não existir, rodar o script de setup
3. Identificar o arquivo de entrada e a operação desejada
4. Construir o comando com a operação e opções
5. Executar o script
6. Confirmar resultado (quantidade de pedaços, dimensões) ao usuário
7. Se auto-split não detectou os elementos corretamente, ajustar `--fuzz`, `--min-size` ou `--split-padding` e tentar novamente
