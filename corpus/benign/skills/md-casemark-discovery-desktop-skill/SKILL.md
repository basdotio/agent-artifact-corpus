---
name: discovery-desktop
description: |
  Development skill for CaseMark's discovery-desktop application - a legal 
  e-discovery platform for document upload, OCR processing, and semantic search. 
  Built with Next.js 16, React 19, Drizzle ORM, and Case.dev APIs. Use this skill 
  when: (1) Working on or extending the discovery-desktop codebase, (2) Integrating 
  with Case.dev APIs for OCR, semantic search, or vault management, (3) Modifying 
  the database schema or queries, (4) Building e-discovery workflow features, or 
  (5) Deploying/configuring the application.
---

# Discovery Desktop Development Guide

A web application for e-discovery teams to manage case vaults, upload legal documents, perform OCR, and execute semantic searches.

**Live site**: https://discovery-desktop.casedev.app/

## Architecture

```
src/
├── app/
│   ├── api/cases/              # Case CRUD operations
│   ├── cases/[caseId]/         # Case dashboard (upload, search, documents)
│   └── page.tsx                # Home - case listing
├── components/
│   ├── ui/                     # shadcn/ui primitives
│   ├── upload/                 # Drag-drop upload, progress tracking
│   └── search/                 # Search bar, results, export
└── lib/
    ├── db/                     # Drizzle schema, client
    ├── casedev/                # Case.dev API wrapper
    └── utils.ts                # cn(), formatters
```

## Core Workflow

```
Create Case → Upload Documents → OCR Processing → Semantic Search → Export
     ↓              ↓                  ↓                ↓              ↓
  Vault API    Case.dev Upload    Automatic via     Natural       CSV with
  password-       bulk             Case.dev API     language      relevance
  protected                                         queries        scores
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, Tailwind CSS |
| Backend | Next.js API Routes |
| Database | SQLite + Drizzle ORM |
| External APIs | Case.dev (Vaults, OCR, Search, LLMs) |
| Deployment | Orbit / Node.js compatible |

## Case.dev API Integration

All document processing uses Case.dev APIs. See [references/casedev-api.md](references/casedev-api.md) for detailed patterns.

### Authentication
```typescript
// lib/casedev/client.ts pattern
const CASEDEV_API_KEY = process.env.CASEDEV_API_KEY;

headers: {
  'Authorization': `Bearer ${CASEDEV_API_KEY}`,
  'Content-Type': 'application/json'
}
```

### Key Operations

| Operation | Purpose |
|-----------|---------|
| Vault Management | Create password-protected storage per case |
| Document Upload | Send files (PDF, DOC, images) for OCR |
| OCR Status | Poll for processing completion |
| Semantic Search | Natural language queries with relevance scores |

## Database Operations

SQLite with Drizzle ORM. See [references/database-schema.md](references/database-schema.md) for complete schema.

### Commands
```bash
npm run db:generate  # Generate migrations from schema changes
npm run db:push      # Push schema to database (dev)
npm run db:studio    # Open Drizzle Studio GUI
```

### Core Tables
- **cases**: id, name, description, passwordHash, vaultId, createdAt
- **documents**: id, caseId, filename, status, casedevDocId, ocrText

## Development

### Setup
```bash
npm install
cp .env.example .env.local
# Add CASEDEV_API_KEY to .env.local
npm run db:push
npm run dev
```

### Environment
```
CASEDEV_API_KEY=sk_case_...   # Required - get from app.case.dev
```

### Build & Deploy
```bash
npm run build
npm start
```

## Common Tasks

### Adding a New API Route
```typescript
// src/app/api/cases/[caseId]/newfeature/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';

export async function POST(
  request: NextRequest,
  { params }: { params: { caseId: string } }
) {
  // Implementation
}
```

### Extending Database Schema
1. Modify `src/lib/db/schema.ts`
2. Run `npm run db:generate`
3. Run `npm run db:push`

### Adding Case.dev Integration
See [references/casedev-api.md](references/casedev-api.md) for endpoint patterns, error handling, and rate limits.

## E-Discovery Context

See [references/ediscovery-glossary.md](references/ediscovery-glossary.md) for legal terminology.

**Key concepts**: Discovery, document production, privilege review, relevance scoring, ESI (electronically stored information).

## Supported File Formats

| Type | Formats |
|------|---------|
| Documents | PDF, DOC, DOCX, TXT |
| Images | JPG, JPEG, PNG, TIFF |
| Bulk | Hundreds of files per upload session |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| OCR stuck | Check Case.dev status, verify file format |
| No search results | Confirm OCR complete, check vault_id |
| Auth errors | Verify CASEDEV_API_KEY |
| Migration fails | Check schema syntax, use `db:push` for dev |
