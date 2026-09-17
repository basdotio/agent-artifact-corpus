---
name: squeleton-skill
description: Lightweight CSS/JS boilerplate with 12-column grid, utility classes for spacing/flexbox/display, WOW/Animated animations, and integrated JS libraries (HTMX, VanJS, Embla, VenoBox, Modals, Toasts). Use for responsive layouts, spacing, modals, carousels and animations. Always prefer Squeleton classes and scripts over writing new CSS/JS.
---

# Squeleton

Boilerplate leve e moderno que combina o melhor do CSS utilitário, grid responsivo, animações elegantes e bibliotecas JavaScript essenciais para criar interfaces rápidas, intuitivas e com manutenção simplificada.

## Princípios Fundamentais

O nome "esqueleto" reflete seu propósito: fornecer a estrutura base para os layouts, evitando que CSS adicional seja escrito para cada nova classe, além de criar componentes HTML reutilizáveis que podem ser transportados entre os projetos que fazem uso do boilerplate.

Ao usar essa habilidade, **sempre prefira usar e combinar as classes do Squeleton ao invés de criar CSS novo**. Para necessidades que geralmente envolvem JavaScript, como Carrosséis, Modais, Ajax, Animações, Notificações Toasts, Reatividade e Cookies, o Squeleton **conta com bibliotecas integradas que podem ser aproveitadas**.

### Perguntas antes de começar

Note que o Squeleton é deliberadamente agnóstico em relação a paleta de cores, família de fontes e estilos muito específicos. Esta neutralidade é uma decisão estratégica para maximizar sua portabilidade entre diferentes temas e projetos. O foco está em fornecer estrutura, grid e utilitários essenciais, deixando a identidade visual para o desenvolvedor definir. 

Ao desenvolver com Squeleton, você pode estar trabalhando em um projeto que já tem o boilerplate integrado e faz uso de arquivos adicionais de estilos e scripts personalizados. Para saber de onde partir, sempre pergunte:

1. Este projeto já possui o Squeleton integrado ou devo incluir seus arquivos via CDN?
2. Este projeto já tem uma folha de estilos adicional (CSS) com cores, família de fontes e formatos exclusivos?
3. Este projeto já tem arquivos JavaScript personalizados além das bibliotecas do Squeleton?
4. Caso existam estilos (CSS) ou scripts (JS) personalizados, pode me indicar os arquivos para que eu os combine da melhor forma com a base do Squeleton?

### Criando CSS ou JS personalizado

Somente crie CSS ou JavaScript novo quando **não existir** uma classe ou biblioteca do Squeleton que resolva a necessidade. Nestes casos:

**Para CSS personalizado:**
- Se estiver trabalhando em um arquivo HTML, adicione uma tag `<style>` no `<head>` do documento
- Se o projeto tiver um arquivo CSS personalizado separado, edite esse arquivo diretamente

**Para JavaScript personalizado:**
- Se estiver trabalhando em um arquivo HTML, adicione uma tag `<script>` antes do fechamento do `</body>`
- Se o projeto tiver um arquivo JS personalizado separado, edite esse arquivo diretamente
- Sempre verifique se as bibliotecas integradas do Squeleton (HTMX, VanJS, Embla, etc.) já resolvem o problema antes de criar código novo

---

## Instalação e Configuração

### Via CDN

```html
<!-- CSS (Head) -->
<link rel="stylesheet" href="https://cdn.squeleton.dev/squeleton.v4.min.css">

<!-- JavaScript (Head) -->
<script src="https://cdn.squeleton.dev/squeleton-main.v4.min.js"></script>

<!-- JavaScript (Footer) -->
<script src="https://cdn.squeleton.dev/squeleton-scripts.v4.min.js"></script>
```

### Arquivos para Download

[squeleton.v4.css](https://cdn.squeleton.dev/squeleton.v4.css) – Versão completa para desenvolvimento (~35KB gzip)
[squeleton.v4.min.css](https://cdn.squeleton.dev/squeleton.v4.min.css) – Versão minificada para produção (~25KB gzip)
[squeleton-main.v4.min.js](https://cdn.squeleton.dev/squeleton-main.v4.min.js) – JavaScript principal (~12KB gzip)
[squeleton-scripts.v4.min.js](https://cdn.squeleton.dev/squeleton-scripts.v4.min.js) – JavaScript secundário (~18KB gzip)

**Consulta direta ao CSS:** Em caso de dúvida sobre a existência de uma classe específica ou para ter uma visão completa da estrutura do framework, consulte diretamente o arquivo `squeleton.v4.css` (versão não-minificada). Isso permite verificar todas as classes disponíveis, seus valores exatos e a organização das media queries.

---

## Estrutura Base CSS

O Squeleton define estilos base em elementos HTML que influenciam o comportamento de layout:

### Reset e Box Model
```css
*, ::after, ::before {
  box-sizing: border-box;
}
```

### Body como Flex Container
```css
body {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-height: 100vh;
}
```

### Main e Section como Flex Containers
```css
main, section {
  display: flex;
  flex-direction: column;
  margin-left: auto;
  margin-right: auto;
  width: 100%;
}
```

### Implicações Práticas

**Importante**: Como `body`, `main` e `section` já são flex containers com `flex-direction: column`:

1. **Classes de alinhamento funcionam no eixo vertical por padrão**:
   - `f-items-center` em `<section>` → centraliza horizontalmente (cross-axis)
   - `f-justify-center` em `<section>` → centraliza verticalmente (main-axis)

2. **Para layout horizontal**, adicione `f-row`:
   ```html
   <!-- Itens lado a lado dentro de section -->
   <section class="f-row f-items-center f-justify-between">
       <div>Esquerda</div>
       <div>Direita</div>
   </section>
   ```

3. **Elementos block dentro de section/main** se empilham naturalmente (comportamento column).

4. **Para centralizar conteúdo em hero sections**:
   ```html
   <!-- Correto: section já é flex-column, só precisa de alinhamento -->
   <section class="h-100vh f-justify-center f-items-center">
       <h1>Centralizado vertical e horizontalmente</h1>
   </section>
   ```

5. **Não é necessário adicionar `d-flex`** em `<body>`, `<main>` ou `<section>` — eles já são flex containers.

---

## Sistema Responsivo Híbrido

O Squeleton usa uma **abordagem híbrida única**: Grid mobile-first + Utilitários desktop-first.

---

## Breakpoints para Colunas de Grid (Mobile-First)

Colunas usam `min-width` - comece em mobile e expanda para desktop:

| Breakpoint | Dimensão | Exemplo |
|------------|----------|---------|
| `c-xs-{1-12}` | ≤ 639px (base) | `c-xs-12` |
| `c-sm-{1-12}` | ≥ 640px | `c-sm-6` |
| `c-md-{1-12}` | ≥ 992px | `c-md-4` |
| `c-lg-{1-12}` | ≥ 1200px | `c-lg-3` |

**⚠️ Sempre inicie com `c-xs-{número}`**: A base mobile é obrigatória para o grid.
- ✅ Correto: `c-xs-12 c-md-6` (100% mobile, 50% desktop)
- ❌ Errado: `c-md-6` (falta o c-xs-)

---

## Breakpoints para Classes Utilitárias (Desktop-First)

**Diferente do grid**, classes utilitárias usam `@max-width` - escreva para desktop, ajuste para mobile:
- Sem prefixo = desktop (padrão)
- Adicione `md-`, `sm-`, `xs-` para ajustar em telas menores
- **Não existe `lg-`** porque desktop já é o padrão

Classes utilitárias criam uma "redução progressiva":

| Breakpoint | Query CSS | Quando Aplica | Exemplo |
|------------|-----------|---------------|---------|
| `xs-` | `@media (max-width: 639px)` | 0px até 639px | `xs-p-20-all` |
| `sm-` | `@media (max-width: 991px)` | 0px até 991px | `sm-d-flex` |
| `md-` | `@media (max-width: 1199px)` | 0px até 1199px | `md-w-50` |
| Sem prefixo | (sem @media) | **Todos os tamanhos** | `p-20-all` |

**⚠️ Comportamento de Sobrescrita por Especificidade**:

Como todos usam `@max-width`, a ordem de especificidade é:
- `xs-` sobrescreve `sm-`, `md-` e global em ≤639px (mais específico)
- `sm-` sobrescreve `md-` e global em ≤991px
- `md-` sobrescreve global em ≤1199px
- Desktop (≥1200px) = usa classe global ou padrão CSS

**Nota**: Não existe `lg-` para classes utilitárias.

### Três padrões de uso:

1. **Sem breakpoint** = global (base para todos os tamanhos)
   ```html
   <div class="p-20-all d-flex w-50">
   <!-- Aplica em todos os tamanhos -->
   ```

2. **Apenas breakpoints** = redução progressiva do maior para menor
   ```html
   <div class="sm-text-center">
   <!-- ≤991px: center | ≥992px: padrão (left) -->

   <div class="xs-text-center sm-text-center">
   <!-- ≤639px: center (xs mais específico)
        640-991px: center (sm)
        ≥992px: padrão (left) -->
   ```

3. **Global + breakpoints** = base global sobrescrita progressivamente
   ```html
   <div class="text-left sm-text-center">
   <!-- ≤991px: center | ≥992px: left (global) -->

   <div class="p-20-all xs-p-30-all">
   <!-- ≤639px: 30px (xs) | ≥640px: 20px (global) -->
   ```

---

## Grid System (12 Colunas)

```html
<div class="container">      <!-- max-width: 1250px, centralizado -->
    <div class="row">        <!-- display: flex, flex-wrap: wrap -->
        <div class="c-xs-12 c-md-8">Conteúdo</div>
        <div class="c-xs-12 c-md-4">Sidebar</div>
    </div>
</div>
```

### Colunas
- Padrão: `c-xs-{1-12}`, `c-sm-{1-12}`, `c-md-{1-12}`, `c-lg-{1-12}`
- Auto: `c-auto` (flex: 1 1 0%)
- Centralizar: `c-center` (margin: 0 auto)

### Containers
- `.container` - max-width: 1250px, centralizado (padrão para conteúdo)
- `.container-fluid` - width: 100% (para seções full-width)

**Quando usar cada um:**
- `container` → Conteúdo centralizado (textos, cards, grids de produtos) - **usar na maioria dos casos**
- `container-fluid` → Conteúdo sem margem lateral (galerias full-width, dashboards, mapas)

### Gaps (espaçamento entre colunas)

O `.row` tem display flex e gap padrão de 30px. Use classes `gap-{valor}` para alterar:

- `.gap-0` - 0px
- `.gap-5` - 5px
- `.gap-10` - 10px
- `.gap-15` - 15px
- `.gap-20` - 20px
- `.gap-25` - 25px
- `.gap-30` - 30px (padrão do row)
- `.gap-35` - 35px
- `.gap-40` - 40px
- `.gap-45` - 45px
- `.gap-50` - 50px
- Responsivos: `{xs|sm|md}-gap-{0-50}` (intervalo de 5)
  - Exemplos: `xs-gap-10`, `sm-gap-20`, `md-gap-0`

**Nota**: O gap aplica espaçamento em ambas as direções (horizontal e vertical) quando colunas quebram de linha.

### Performance - Content Visibility (Lazy Rendering)

Classes `.render-auto`, `.render-auto-small`, `.render-auto-large` para otimizar containers below-the-fold usando `content-visibility: auto`. Aplicar em `.container` ou `.container-fluid`. Consulte `references/grid-reference.md` para detalhes.

---

## Classes Utilitárias de Padding (p-) e Margin (m-)
**Padrão**: `{p|m}-{valor}-{direção}`

| Direção | Aplicação |
|---------|-----------|
| `-all` | Todos os lados |
| `-t` | Top |
| `-b` | Bottom |
| `-l` | Left |
| `-r` | Right |
| `-tb` | Top + Bottom |
| `-lr` | Left + Right |

**Valores**: 0, 5, 10, 15, 20, 25, 30... até 100 (intervalo de 5)
- Os números representam pixels diretos: `p-20-all` = padding de 20px
- Responsivo: `xs-`, `sm-`, `md-` ou sem prefixo (desktop)

```html
<div class="p-20-tb m-10-lr">Padding 20px vertical, margin 10px horizontal</div>
<div class="xs-p-10-all md-p-30-all">10px mobile, 30px tablet+</div>
<div class="m-50-b p-15-lr">Margem 50px abaixo, padding 15px lateral</div>
<div class="xs-m-5-t sm-m-15-t m-40-t">Margem top progressiva: 5px → 15px → 40px</div>
```

**Margin Auto (centralização)**:
```html
<div class="m-auto-lr">Centralizado horizontalmente</div>
```

Consulte `references/padding-reference.md` e `references/margin-reference.md` para mais informações e exemplos.

---

## Classes Utilitárias de Width (w-)

**Width em Pixels** - `w-{valor}px`:
- 5px até 100px (intervalo de 5px)
- 100px até 300px (intervalo de 10px)
- 300px até 900px (intervalo de 50px)
- Responsivos: `md-w-{valor}px`, `sm-w-{valor}px`, `xs-w-{valor}px`

**Width Percentual** - `w-{valor}` (sem unidade):
- 10% até 100% (intervalo de 5%)
- Responsivos: `md-w-{valor}`, `sm-w-{valor}`, `xs-w-{valor}`

**Width Especiais**:
- `w-auto` - largura automática
- Responsivos: `md-w-auto`, `sm-w-auto`, `xs-w-auto`

> Todas as classes `w-*px` incluem `max-width: 100%` automaticamente, evitando overflow horizontal em telas menores.

```html
<!-- Largura fixa -->
<div class="w-250px">250px de largura</div>

<!-- Largura percentual responsiva -->
<div class="w-50 xs-w-100">50% desktop, 100% mobile</div>

<!-- Modal com largura controlada -->
<div class="w-600px">Modal centrado</div>
```

Consulte `references/width-reference.md` para lista completa de valores.

---

## Classes Utilitárias de Height (h-)

**Height em Pixels** - `h-{valor}px`:
- 5px até 100px (intervalo de 5px)
- 100px até 300px (intervalo de 10px)
- 300px até 900px (intervalo de 50px)
- Responsivos: `md-h-{valor}px`, `sm-h-{valor}px`, `xs-h-{valor}px`

**Height Percentual e Especiais**:
- `h-50` (min-height: 50%)
- `h-100` (min-height: 100%)
- `h-100vh` (min-height: 100vh) - **útil para hero sections**
- `h-100dvh` (min-height: 100dvh) - **melhor para mobile**
- `h-auto` (min-height: auto)
- Responsivos: `md-h-{valor}`, `sm-h-{valor}`, `xs-h-{valor}`

```html
<!-- Hero section altura total -->
<section class="h-100vh f-items-center">Hero</section>

<!-- Cards com mesma altura -->
<div class="row">
    <div class="c-md-4"><div class="card h-100">Card 1</div></div>
    <div class="c-md-4"><div class="card h-100">Card 2</div></div>
</div>

<!-- Altura fixa -->
<div class="h-300px">300px de altura</div>
```

Consulte `references/height-reference.md` para lista completa de valores.

---

## Classes Utilitárias de Display (d-)
```html
<div class="d-none">Oculto</div>
<div class="d-block">Block</div>
<div class="d-inline">Inline</div>
<div class="d-inline-block">Inline-block</div>
<div class="d-flex">Flex</div>
<div class="d-inline-flex">Inline Flex</div>
<div class="d-grid">Grid</div>
<div class="d-contents">Contents</div>
<div class="d-table">Table</div>
<div class="d-table-cell">Table Cell</div>
<div class="xs-d-none md-d-block">Oculto mobile, visível desktop</div>
```

Consulte `references/display-reference.md` para mais informações e exemplos.

---

## Classes Utilitárias de Flexbox (f-)
**Container**:
- `.f-grid` - display: flex + wrap + row (ideal para layouts)
- `.d-flex` - display: flex
- `.f-row`, `.f-col` - direção
- `.f-wrap`, `.f-nowrap` - quebra de linha

**Alinhamento**:
- `.f-items-center`, `.f-items-start`, `.f-items-end` - align-items (dentro de cada linha)
- `.f-justify-center`, `.f-justify-between`, `.f-justify-evenly` - justify-content (eixo principal)
- `.f-content-center`, `.f-content-between`, `.f-content-around` - align-content (múltiplas linhas)
- `.f-self-center`, `.f-self-start`, `.f-self-end` - align-self individual

**Crescimento**:
- `.f-grow-1`, `.f-grow-2`, `.f-grow-3`
- `.f-shrink-0`, `.f-shrink-1`
- `.f-auto-max` (flex: 1 1 auto)
- `.f-auto-min` (flex: 0 1 auto)

**Gaps flex**: `.f-gap-{0-50}` (intervalo de 5)

```html
<!-- Centralizar conteúdo -->
<div class="d-flex f-items-center f-justify-center h-100vh">
    Centralizado
</div>

<!-- Header com logo e menu -->
<header class="d-flex f-items-center f-justify-between p-20-tb">
    <div class="logo">Logo</div>
    <nav class="d-flex f-gap-20">...</nav>
</header>
```

Consulte `references/flex-reference.md` para mais informações e exemplos.

---

## Classes Utilitárias de Border

**Border Completo e por Lado**:
- `.border-all` - borda em todos os lados (1px solid)
- `.border-t`, `.border-b`, `.border-l`, `.border-r` - borda em um lado
- `.border-tb` - borda top e bottom
- `.border-lr` - borda left e right

**Border Width**:
- `.border-w-{1-5}` - espessura de 1px a 5px

**Border Style**:
- `.border-solid`, `.border-dashed`, `.border-dotted`
- `.border-none`, `.border-hidden`, `.border-transparent`

**Remover Border**:
- `.border-0-{t|b|l|r|all}`
- Responsivos: `{xs|sm|md}-border-0-*`

**Border Radius**:
- `.border-rd-{0-20}` - 0px a 20px (1 em 1)
- `.border-rd-50`, `.border-rd-100` - circular (50%)
- `.border-rd-{valor}-t` - só cantos superiores (valores pares: 0, 2, 4... 20)
- `.border-rd-{valor}-b` - só cantos inferiores (valores pares: 0, 2, 4... 20)
- Responsivos: `{xs|sm|md}-border-rd-*` (mesmos padrões acima)

## Classes Utilitárias de Opacity

**Opacity de Elemento**:
- `.opacity-{1-9}` - onde 1 = 0.15 e 9 = 0.9

**Opacity Background (overlay absoluto)**:
- `.opacity-bg-{0-10}` - overlay com position absolute
- 0 = opacity 1 (opaco), 10 = opacity 0 (transparente)
- Útil para overlays sobre imagens

## Classes Utilitárias de Z-Index
- `.z-index-{0-5}` - z-index de 0 a 5
- `.z-index-111`, `.z-index-1111` - valores altos
- `.z-index-minus-2` - z-index negativo (-2)

## Classes Utilitárias de Tipografia

**Font Size - Escala Numérica (fs-1 a fs-16)**:
- `.fs-1` a `.fs-6` - tamanhos fixos (10px a 15px)
- `.fs-7` a `.fs-16` - tamanhos fluidos com clamp() (16px a 64px)
- Responsivos: `md-fs-{1-16}`, `sm-fs-{1-16}`, `xs-fs-{1-16}`

| Classe | Tamanho | Uso |
|--------|---------|-----|
| `.fs-1` | 10px | Micro labels |
| `.fs-2` | 11px | Badges |
| `.fs-3` | 12px | Small text |
| `.fs-4` | 13px | Secondary |
| `.fs-5` | 14px | Body small |
| `.fs-6` | 15px | Body alt |
| `.fs-7` | 15→16px | Body padrão |
| `.fs-8` | 16→17px | Body large |
| `.fs-9` | 17→18px | Lead |
| `.fs-10` | 18→20px | Subtítulo |
| `.fs-11` | 21→24px | Título pequeno |
| `.fs-12` | 24→28px | Título médio |
| `.fs-13` | 28→32px | Título grande |
| `.fs-14` | 34→40px | Headline |
| `.fs-15` | 40→48px | Hero |
| `.fs-16` | 52→64px | Display |

**Exemplo responsivo**:
```html
<h1 class="fs-14 md-fs-12 sm-fs-10 xs-fs-8">Título que escala com a tela</h1>
```

**Font Weight e Espaçamento**:
- `.fw-{300-900}` - font-weight (300, 400, 500, 600, 700, 800, 900)
- `.ls-{0-5}` - letter-spacing positivo
- `.ls-minus-{0-2|0-5|1|2|3}` - letter-spacing negativo

**Font Size - Ajustes Percentuais**:
- `.minus-{10-50}` - font-size menor (50-90%)
- `.more-{10-50}` - font-size maior (110-150%)

**Alinhamento e Transformação**:
- `.text-left`, `.text-center`, `.text-right`
- `.text-uppercase`, `.text-lowercase`
- `.lh-1-{0-9}` - line-height (1.0 a 1.9)

## Classes Utilitárias de Posicionamento
- `.ps-relative`, `.ps-absolute`, `.ps-fixed`, `.ps-sticky`, `.ps-static`
- `.top-0`, `.bottom-0`, `.left-0`, `.right-0`, `.top-auto`, `.bottom-auto` - valores de posição
- `.absolute-xy` - centraliza absoluto (transform translate -50%)

## Outras Classes Utilitárias

- **Cursor**: `.cursor-pointer`, `.cursor-grab`, `.cursor-not-allowed`, etc.
- **Imagem**: `.obj-cover`, `.obj-contain`, `.aspect-16-9`, `.aspect-1-1`, etc.
- **Texto**: `.truncate`, `.line-clamp-2`, `.line-clamp-3`
- **Interação**: `.pe-none`, `.pe-auto`
- **Visibilidade**: `.visible-xs`, `.visible-sm`, `.visible-md`, `.visible-lg` - mostra apenas no breakpoint
- **Vídeo**: `.video-responsive`, `.embed-responsive-16by9` - iframes/vídeos responsivos

Consulte `references/utilities-reference.md` para lista completa.

---

## Animações

### Com WOW (ativa ao entrar no viewport)
```html
<div class="wow fadeInUp">Anima ao scroll</div>
<div class="wow bounceIn" data-wow-delay="0.2s">Com delay</div>
<div class="wow pulse" data-wow-iteration="3">3 vezes</div>
```

### Com Animated (ativa imediatamente)
```html
<div class="animated fadeIn">Imediato</div>
<div class="animated pulse infinite">Loop infinito</div>
<div class="animated zoomIn delay-500 duration-2000">Com delay e duração</div>
```

**Animações disponíveis**:
- **Fade**: fadeIn, fadeInUp, fadeInDown, fadeInLeft, fadeInRight, fadeOut
- **Bounce/Zoom**: bounceIn, zoomIn, zoomOut
- **Rotate/Flip**: rotateIn, flipIn
- **BackIn**: backInDown, backInLeft, backInRight, backInUp
- **Special**: glowIn, slideIn, popIn, liquidIn, magnetIn, floatIn, waveIn
- **Attention**: flash, pulse, shakeX, swing, tada

**Classes auxiliares**:
- `.delay-{100-5000}` (100, 200, 250, 300... 1000, 1250, 1500...)
- `.duration-{500-3000}`
- `.repeat-{2-5}`, `.infinite`
- `.reverse`, `.alternate`

**Animações contínuas prontas**: `.anima-pulse`, `.anima-shake`, `.anima-heart`, `.anima-skeleton`

Consulte `references/animations-reference.md` para mais informações e exemplos.

---

## Bibliotecas JavaScript

O Squeleton integra bibliotecas JavaScript otimizadas e pré-configuradas:

| Biblioteca | Finalidade | GitHub |
|------------|------------|--------|
| **HTMX** | Requisições AJAX declarativas via atributos HTML. Ver `references/htmx-reference.md` | github.com/bigskysoftware/htmx |
| **Embla Carousel** | Carrossel minimalista com swipe fluido. Ver `references/carousel-reference.md` | github.com/davidjerleke/embla-carousel |
| **js-cookie** | Gerenciamento de cookies do navegador. Ver `references/cookies-reference.md` | github.com/js-cookie/js-cookie |
| **a11y-dialog** | Modais acessíveis e leves. Ver `references/modal-reference.md` | github.com/KittyGiraudel/a11y-dialog |
| **VanJS** | Framework reativo minimalista. Ver `references/vanjs-reference.md` | github.com/vanjs-org/van |
| **Toastify** | Notificações toast customizáveis. Ver `references/toastify-reference.md` | github.com/apvarun/toastify-js |
| **VenoBox 2** | Lightbox para imagens, vídeos e galerias. Ver `references/venobox-reference.md` | github.com/nicholasio/venobox |
| **Counter-Up2** | Animação de contagem numérica. Ver `references/counter-reference.md` | github.com/bfintal/Counter-Up2 |
| **Wow2 Animation** | Animações on-scroll. Ver `references/animations-reference.md` | github.com/graingert/wow |

---

### Modais com a11y-dialog

Modais com classe `.modal-dialog` já vêm com scroll lock automático (eventos show/hide).

**Configuração a11y-dialog**: Os atributos originais `data-a11y-dialog-*` foram renomeados para `data-modal-*`:

| Original | Squeleton |
|----------|-----------|
| `data-a11y-dialog` | `data-modal` |
| `data-a11y-dialog-show` | `data-modal-show` |
| `data-a11y-dialog-hide` | `data-modal-hide` |

Veja exemplo completo em "Padrões Comuns de Uso" > "Modal Centralizado". Consulte `references/modal-reference.md` para mais opções.

---

## Ícones

Prefixo: `iccon-{nome}-{variante}`

```html
<span class="iccon-home-1"></span>
<span class="iccon-user-2"></span>
```

**IMPORTANTE**: Use APENAS ícones da lista oficial em `references/icons-reference.md`. Ícones inventados ou de outros frameworks NÃO funcionarão. **SEMPRE consulte a referência ANTES de usar qualquer ícone.**

Consulte `references/icons-reference.md` para a lista completa organizada por categoria.

## Tooltips

Tooltips em CSS puro baseados na Balloon.css (já integrada):

```html
<button aria-label="Texto do tooltip" data-balloon-pos="up">Hover aqui</button>
```

Posições: `up`, `down`, `left`, `right`, `up-left`, `up-right`, `down-left`, `down-right`

Consulte `references/tooltips-reference.md` para mais opções.

## Padrões Comuns de Uso

### Hero Section Full Height
```html
<section class="h-100vh f-items-center f-justify-center text-center p-30-all">
    <div class="w-600px">
        <h1 class="fs-13 fw-700 m-20-b">Título Principal</h1>
        <p class="fs-9 opacity-8">Subtítulo descritivo</p>
    </div>
</section>
```

### Grid de Cards Responsivo
```html
<section class="p-60-tb">
    <div class="container p-60-tb xs-p-30-tb render-auto">
        <div class="row gap-10">
            <div class="c-xs-12 c-sm-6 c-lg-3">
                <div class="border-all border-rd-8 p-20-all cursor-pointer">
                    <img src="produto.jpg" class="w-100 border-rd-4 m-15-b">
                    <h4 class="fs-5 m-10-b">Nome do Produto</h4>
                    <p class="fs-9 fw-700">R$ 99,90</p>
                </div>
            </div>
            <!-- Repetir para 20+ produtos -->
        </div>
    </div>
</section>
```

### Header com Logo e Menu
```html
<header class="p-20-tb border-b">
    <div class="container">
        <div class="d-flex f-items-center f-justify-between">
            <div class="logo">
                <img src="logo.svg" class="h-40px">
            </div>
            <nav class="d-flex f-gap-20 xs-d-none">
                <a href="#" class="cursor-pointer">Home</a>
                <a href="#" class="cursor-pointer">Sobre</a>
                <a href="#" class="cursor-pointer">Contato</a>
            </nav>
        </div>
    </div>
</header>
```

### Modal Centralizado
```html
<!-- Trigger -->
<button data-modal-show="exemplo-modal" class="cursor-pointer">Abrir Modal</button>

<!-- Modal -->
<div data-modal="exemplo-modal" class="modal-dialog" aria-hidden="true">
    <div class="dialog-content">
        <div class="dialog-backdrop" data-modal-hide></div>
        <div class="dialog-inline w-500px">
            <button class="dialog-close" data-modal-hide></button>
            <div class="modal-popup border-rd-10 p-30-all">
                <h3 class="fs-11 m-20-b">Título do Modal</h3>
                <p>Conteúdo...</p>
            </div>
        </div>
    </div>
</div>
```

### Carrossel com Embla

Embla Carousel **requer inicialização via JavaScript**. Estrutura HTML:

```html
<div class="slide__viewport">
    <div class="slide__row gap-15">
        <div class="slide__item c-xs-12 c-sm-6 c-md-4">
            <img src="slide1.jpg" class="w-100">
        </div>
        <div class="slide__item c-xs-12 c-sm-6 c-md-4">
            <img src="slide2.jpg" class="w-100">
        </div>
    </div>
    <div class="slide__dots"></div>
    <button class="slide__prev"><span class="iccon-chevron-left-1"></span></button>
    <button class="slide__next"><span class="iccon-chevron-right-1"></span></button>
</div>
```

Consulte `references/carousel-reference.md` para inicialização e opções avançadas.

### Lightbox com VenoBox

VenoBox já vem inicializado com os seletores: `.open-gallery`, `.open-video`, `.open-iframe`

```html
<!-- Galeria de imagens -->
<a href="foto1.jpg" class="open-gallery" data-gall="galeria1"><img src="thumb1.jpg"></a>
<a href="foto2.jpg" class="open-gallery" data-gall="galeria1"><img src="thumb2.jpg"></a>

<!-- Vídeo -->
<a href="https://youtube.com/watch?v=xxx" class="open-video">Ver vídeo</a>

<!-- Iframe -->
<a href="pagina.html" class="open-iframe">Abrir iframe</a>
```

Consulte `references/venobox-reference.md` para mais opções.

---

## Arquivos de Referência

Para lista completa de todas as classes disponíveis, consulte os arquivos em [references/](references/):

- [grid-reference.md](references/grid-reference.md) - Sistema de grid de 12 colunas
- [display-reference.md](references/display-reference.md) - Classes de display, overflow e position
- [flex-reference.md](references/flex-reference.md) - Flexbox completo
- [padding-reference.md](references/padding-reference.md) - Todas as classes de padding
- [margin-reference.md](references/margin-reference.md) - Todas as classes de margin
- [width-reference.md](references/width-reference.md) - Largura e max-width
- [height-reference.md](references/height-reference.md) - Altura e min-height
- [typography-reference.md](references/typography-reference.md) - Tipografia e texto
- [border-reference.md](references/border-reference.md) - Bordas, radius, opacity e z-index
- [utilities-reference.md](references/utilities-reference.md) - Position, visibility, float, background
- [animations-reference.md](references/animations-reference.md) - Animações WOW e Animated
- [icons-reference.md](references/icons-reference.md) - Todos os ícones organizados por categoria
- [modal-reference.md](references/modal-reference.md) - Modal (a11y-dialog)
- [carousel-reference.md](references/carousel-reference.md) - Carrossel (Embla)
- [venobox-reference.md](references/venobox-reference.md) - Lightbox (VenoBox)
- [tooltips-reference.md](references/tooltips-reference.md) - Tooltips (Balloon.css)
- [counter-reference.md](references/counter-reference.md) - Contagem animada (Counter-Up2)
- [htmx-reference.md](references/htmx-reference.md) - Requisições AJAX (HTMX)
- [cookies-reference.md](references/cookies-reference.md) - Gerenciamento de cookies (js-cookie)
- [vanjs-reference.md](references/vanjs-reference.md) - Framework reativo (VanJS)
- [toastify-reference.md](references/toastify-reference.md) - Notificações toast (Toastify)
