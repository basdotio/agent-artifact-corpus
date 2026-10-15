# Guías de Frontend (Habi)

Este directorio consolida las guías del stack de frontend de Habi. Aplica a proyectos Next.js 15
(App Router) entregados como frontend estático (SSG) en S3 + CloudFront.

## Stack y convenciones

- Next.js 15 con App Router, solo Client Components
- Renderizado: SSG (sin SSR/ISR)
- Datos: REST; fetch/axios desde cliente; SWR recomendado
- Estilos: Tailwind v4 + Keychain (DS de Habi)
- Formularios/validación: react-hook-form + zod
- Imágenes/Fuentes: `next/image` y `next/font`
- Ruteo: `<Link prefetch>` cuando aplique
- Calidad: ESLint (default), Prettier, TypeScript `strict: true`
- Paquetes: `pnpm` preferido (o `npm`)
- Imports absolutos: alias `@/*`
- Observabilidad: Sentry (pendiente documentar)

## Documentos

- Next.js (frontend-only): `next-js.mdc`
- Estado (Zustand): `zustand.mdc`
- Tailwind v4 + tokens: `tailwind.mdc`

## TODOs pendientes

- Integración DevOps de despliegue (SSG a S3 + CloudFront, invalidaciones, cache policies):
  documentar en PR futuro
- Alineación completa con Keychain (tokens y componentes) + Figma Connect
- Observabilidad (Sentry + source maps): documentar

## Ejemplo

Proyecto de ejemplo con Next 15: `examples/next15-frontend`.
