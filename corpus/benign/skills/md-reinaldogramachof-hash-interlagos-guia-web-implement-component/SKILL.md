---
name: implement-component
description: Implementa um componente React seguindo o design system e padrões de arquitetura do projeto. Use quando o Claude definir um novo componente a ser criado (View, Card, Modal, ou componente genérico).
argument-hint: [tipo: view|card|modal|component] [nome]
---

Implemente o componente `$ARGUMENTS` seguindo os padrões do projeto.

## Checklist pré-implementação

Antes de escrever uma linha de código, confirme:
- [ ] Onde o arquivo vai: `features/{dominio}/` ou `components/`?
- [ ] Qual é o caminho relativo para imports (`../../services/`, `../../components/`)?
- [ ] Quais dados este componente precisa? Via service ou via props?
- [ ] O componente vai exceder 200 linhas? Se sim, dividir antes de começar.

## Regras por tipo de componente

### View (`{Nome}View.jsx`)
```jsx
import { SkeletonCard } from '../../components/SkeletonCard';
import EmptyState from '../../components/EmptyState';
import { fetch[Entidade] } from '../../services/[entidade]Service';

// Container raiz SEMPRE com pb-24 (espaço para Bottom Nav)
<div className="pb-24">
  {loading && <SkeletonCard count={5} />}
  {!loading && items.length === 0 && (
    <EmptyState icon="📭" title="Nenhum item" description="..." />
  )}
</div>
```

### Card (`{Nome}Card.jsx`)
```jsx
// Usar design tokens — NUNCA valores hardcoded
<div className="bg-white rounded-card shadow-card border border-gray-100 p-4">
  <img loading="lazy" ... />
  // Botão com área de toque mínima
  <button className="min-h-[44px] px-4 rounded-pill bg-brand-600 text-white">
```

### Modal (`{Nome}DetailModal.jsx`)
```jsx
// Imagem responsiva — NUNCA h-64 fixo
<div className="h-48 sm:h-64 ...">

// Título responsivo — NUNCA text-4xl
<h2 className="text-2xl sm:text-3xl font-bold">

// Fechar com Escape e backdrop
useEffect(() => {
  const handleEsc = (e) => { if (e.key === 'Escape') onClose(); };
  document.addEventListener('keydown', handleEsc);
  return () => document.removeEventListener('keydown', handleEsc);
}, []);
```

### Componente Genérico (`components/{Nome}.jsx`)
- Sem lógica de negócio (sem chamadas a services)
- Recebe tudo via props
- Exportar como `export default`

## Regras Mobile-First

- Começar sempre com classes base (mobile 375px)
- Adicionar `sm:`, `md:`, `lg:` apenas para adaptar para telas maiores
- Texto mínimo: `text-sm` — nunca menor que isso em conteúdo
- Botões: `min-h-[44px]` para área de toque adequada

## Ao finalizar

1. Contar linhas do arquivo — se > 200, extrair sub-componentes
2. Verificar todos os imports estão corretos
3. Se é uma View: adicionar ao switch em `App.jsx`
4. Rodar `cd app && npm run build`
5. Reportar walkthrough completo ao Claude
