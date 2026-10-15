# Next 15 Frontend Example (SSG)

Ejemplo mínimo de frontend con Next.js 15 (App Router), SSG (`output: "export"`), Tailwind v4, alias
`@/*`, y SWR provider.

## Requisitos

- Node 18+
- npm / pnpm (este ejemplo usa npm)

## Comandos

```bash
npm run dev       # desarrollo (Turbopack)
npm run build     # build SSG (out/)
npm start         # sirve la carpeta out/ localmente
```

## Configuración clave

- `next.config.ts`:

  - `output: 'export'`, `images.unoptimized: true`
  - `trailingSlash: true` (recomendado para S3/CloudFront)
  - `basePath` opcional vía `NEXT_PUBLIC_BASE_PATH`

- `tsconfig.json`:

  - `strict: true`, alias `@/*` a `src/*`

- `src/app/layout.tsx` y `src/app/providers.tsx`:
  - Provider de SWR global (cliente)

## Variables de entorno

Crear `.env.local` si necesitas subruta:

```env
NEXT_PUBLIC_BASE_PATH=/tu-subruta
```

## TODOs

- Integración DevOps (deploy a S3 + CloudFront, invalidaciones y cache policies) — documentar en PR
  futuro
- Alineación de tokens con Keychain + Figma Connect (ver guía Tailwind)
