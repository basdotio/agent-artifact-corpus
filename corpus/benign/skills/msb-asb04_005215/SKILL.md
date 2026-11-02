---
name: database
description: PostgreSQL VPS database expert. Manages database creation, Prisma schemas, migrations, seeding. Auto-activates on keywords "database", "postgresql", "prisma", "db", "sql" or when backend with data storage needed.
allowed-tools: Bash, Read, Write, Edit
---

# Database Management Skill

> **PostgreSQL VPS + Prisma Expert**
>
> Inspiré de : Prisma Best Practices, PostgreSQL Standards, Database-per-Service Pattern

---

## Scope & Activation

**Chargé par:** EXECUTOR agent (backend avec database)

**Auto-activé si keywords:**
- `database`, `db`, `postgresql`, `postgres`, `sql`
- `prisma`, `schema`, `migration`, `model`
- Backend nécessite stockage données
- User mentionne "VPS", "database"

**Gère:**
- Connexion PostgreSQL VPS
- Création databases
- Génération Prisma schemas
- Migrations
- Seeding données test
- Backup/restore

---

## PostgreSQL VPS Architecture (RÈGLES STRICTES)

### Instances PostgreSQL Disponibles

**❌ NE PAS UTILISER:**
- Port **5432**: Container Docker `agi_postgres` (réservé projet AGI uniquement)
- Port **5434**: ~~Ancien container mcp-memory~~ (SUPPRIMÉ - n'existe plus)

**✅ UTILISER UNIQUEMENT:**
- Port **5433**: Container Docker `blv-postgres` (TOUS les projets BUILDER/BLV/etc.)

### Credentials PostgreSQL VPS (HARDCODÉS)

**Instance PostgreSQL Production (Port 5433):**

```bash
# VPS IP
HOST="89.116.27.88"

# Port (UNIQUE pour tous projets)
PORT="5433"

# User
USER="pentester"

# Password
PASSWORD="Voiture789"

# Database par défaut (pour créer nouvelles DB)
DEFAULT_DB="postgres"
```

**⚠️ RÈGLES ABSOLUES:**

1. **TOUJOURS utiliser port 5433** (jamais 5432, jamais 5434)
2. **TOUJOURS utiliser user pentester** (jamais pilote, jamais postgres)
3. **TOUJOURS utiliser password Voiture789**
4. **JAMAIS hardcoder DATABASE_URL dans schema.prisma** (toujours `env("DATABASE_URL")`)
5. **1 projet = 1 database dédiée** (isolation complète)

### Databases Existantes (Port 5433)

Au 2025-01-12, databases créées:
- `postgres` (default PostgreSQL)
- `builder_dashboard` (BUILDER frontend - Kanban/Todo/Tasks)
- `blv` (Projet BLV)
- `memory` (MCP gestion - Memory RAG + PostgreSQL tools)
- `NEURODOPA` (Projet neuro)
- `admin_kanban_db` (Admin kanban)
- `task_timer_db` (Task timer)

**Vérifier avant créer:**
```typescript
// ✅ OBLIGATOIRE: Utiliser MCP gestion
mcp__gestion__postgresql_list_databases()
```

---

## 🔧 MCP Gestion PostgreSQL Tools (RÉFÉRENCE)

**Tools disponibles (9 outils):**

### 1. List Databases
```typescript
mcp__gestion__postgresql_list_databases()
// Retourne: {"databases": [...], "count": N}
```

### 2. Create Database
```typescript
mcp__gestion__postgresql_create_database("nom_projet_db")
// owner par défaut: "pentester" (correct)
// Retourne: "✓ Database created: nom_projet_db (owner: pentester)"
```

### 3. Get Connection URL
```typescript
mcp__gestion__postgresql_get_connection_url("nom_projet_db")
// Defaults: pentester/Voiture789@89.116.27.88:5433
// Retourne: {
//   "database": "nom_projet_db",
//   "url": "postgresql://pentester:Voiture789@89.116.27.88:5433/nom_projet_db",
//   "env_format": "DATABASE_URL=\"postgresql://...\""
// }
```

### 4. Get Schema
```typescript
mcp__gestion__postgresql_get_schema("nom_projet_db")
// Retourne: {"tables": [{name, columns}], "table_count": N}
```

### 5. Query (SELECT)
```typescript
mcp__gestion__postgresql_query("nom_projet_db", "SELECT * FROM users LIMIT 5")
// Retourne: {"rows": [...], "count": N}
```

### 6. Execute (DDL/DML)
```typescript
mcp__gestion__postgresql_execute("nom_projet_db",
  "CREATE TABLE users (id SERIAL PRIMARY KEY, email TEXT)")
// ⚠️ Dangereux - Utilise avec précaution
```

### 7. Create Table (Helper)
```typescript
mcp__gestion__postgresql_create_table("nom_projet_db", "users",
  "id SERIAL PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT, created_at TIMESTAMP DEFAULT NOW()")
// Retourne: "✓ Table users created"
```

### 8. Insert Row (Helper)
```typescript
mcp__gestion__postgresql_insert_row("nom_projet_db", "users",
  {"email": "admin@example.com", "name": "Admin User"})
// Retourne: {"inserted_row": {...}, "message": "✓ Row inserted"}
```

### 9. Validate Connection
```typescript
mcp__gestion__postgresql_validate_connection("nom_projet_db")
// Retourne: {"version": "PostgreSQL 16.10", "connected": true}
```

**⚠️ IMPORTANT:**
- Tous les tools utilisent automatiquement `pentester/Voiture789@89.116.27.88:5433`
- Pas besoin de passer credentials manuellement
- MCP = Source de vérité (évite erreurs credentials)

---

## Architecture Database (STRICT)

### Règle #1: 1 Projet = 1 Database Dédiée

**❌ INTERDIT:**
```
postgres
├── schema: project1
├── schema: project2  ← JAMAIS mélanger projets
└── schema: project3
```

**✅ CORRECT:**
```
Database: project1_db
├── schema: public (défaut PostgreSQL)
│   ├── table: users
│   ├── table: tasks
│   └── table: sessions

Database: project2_db
├── schema: public
│   ├── table: products
│   └── table: orders
```

**Principe:** Isolation complète. Chaque projet a sa propre database.

---

### Règle #2: Naming Convention Databases

**Format:** `[nom_projet]_db`

**Exemples:**
- Projet "time-master" → Database `time_master_db`
- Projet "task-manager" → Database `task_manager_db`
- Projet "dashboard-admin" → Database `dashboard_admin_db`

**Caractères autorisés:** `[a-z0-9_]` (lowercase, chiffres, underscore uniquement)

---

---

## ⚠️ WORKFLOW OBLIGATOIRE (Non-Negotiable)

### Phase 0: MCP Gestion (TOUJOURS EN PREMIER)

**❌ INTERDIT:**
- Créer database via `createdb` CLI
- Créer database via SQL direct (`psql -c "CREATE DATABASE"`)
- Écrire credentials manuellement dans `.env`

**✅ OBLIGATOIRE:**
- **TOUJOURS utiliser MCP gestion tools**
- MCP = Source de vérité PostgreSQL
- MCP garantit conventions (port 5433, user pentester, UTF8)

**Workflow strict:**

```typescript
// STEP 1: Check si database existe
mcp__gestion__postgresql_list_databases()

Response:
{
  "databases": ["postgres", "builder_dashboard", "blv", "memory", ...],
  "count": 8
}

// STEP 2: SI database absente → Créer
mcp__gestion__postgresql_create_database("nom_projet_db")

Response:
{
  "success": true,
  "database": "nom_projet_db",
  "owner": "pentester",
  "message": "✓ Database created: nom_projet_db"
}

// OU SI existe déjà:
{
  "info": "ℹ️ Database already exists: nom_projet_db"
}

// STEP 3: Obtenir DATABASE_URL
mcp__gestion__postgresql_get_connection_url("nom_projet_db")

Response:
{
  "database": "nom_projet_db",
  "url": "postgresql://pentester:Voiture789@89.116.27.88:5433/nom_projet_db",
  "env_format": "DATABASE_URL=\"postgresql://pentester:Voiture789@89.116.27.88:5433/nom_projet_db\""
}

// STEP 4: Écrire .env automatiquement
Write .env avec DATABASE_URL exacte du MCP
```

**Avantages MCP:**
- ✅ Credentials toujours corrects (port 5433, pentester)
- ✅ Check existence automatique (pas de duplication)
- ✅ Format DATABASE_URL garanti cohérent
- ✅ Historique centralisé (MCP logs toutes opérations)

---

### Phase 1: Validation Prisma Schema (AVANT db push)

**❌ INTERDIT:**
- Écrire `schema.prisma` puis direct `npx prisma db push`
- Skiper validation TypeScript
- Ignorer erreurs Prisma

**✅ OBLIGATOIRE:**
- Valider schema AVANT push
- Check TypeScript compile
- Fix erreurs AVANT continuer

**Workflow validation:**

```bash
# STEP 1: Écrire schema.prisma selon conventions
# (voir section Prisma Schema Generation plus bas)

# STEP 2: Valider syntax Prisma
npx prisma validate

# Output attendu:
# ✓ Schema is valid

# STEP 3: Format auto schema
npx prisma format

# STEP 4: Générer Prisma Client
npx prisma generate

# Output attendu:
# ✓ Generated Prisma Client

# STEP 5: Check TypeScript compile (zero errors)
npx tsc --noEmit

# Output attendu:
# (vide = 0 errors)

# STEP 6: SEULEMENT si TOUT passe → Push DB
npx prisma db push

# Output attendu:
# 🚀 Your database is now in sync with your Prisma schema
```

**SI erreurs TypeScript:**
```bash
npx tsc --noEmit

# Exemple erreur:
# error TS2339: Property 'column' does not exist on type 'KanbanTask'

# → FIX: Ajouter relation dans schema.prisma
# → Re-valider (STEP 2-6)
# → JAMAIS passer à l'étape suivante avec erreurs
```

---

### Phase 2: Relations Prisma (TOUJOURS Bidirectionnelles)

**❌ INTERDIT:**

```prisma
// ❌ Foreign key SANS relation
model KanbanTask {
  id       String @id @default(cuid())
  columnId String  // ← Juste FK, pas de relation
}

model KanbanColumn {
  id String @id @default(cuid())
  // ← Pas de tasks[] relation
}
```

**Problème:** TypeScript compile mais runtime crashes:
```typescript
// ❌ CRASH runtime
const column = await prisma.kanbanColumn.findUnique({
  include: { tasks: true }  // Property 'tasks' does not exist
})
```

**✅ CORRECT:**

```prisma
// ✅ Relations bidirectionnelles complètes
model KanbanTask {
  id       String       @id @default(cuid())
  columnId String
  column   KanbanColumn @relation(fields: [columnId], references: [id], onDelete: Cascade)

  @@index([columnId])  // ✅ Index sur FK (performance)
}

model KanbanColumn {
  id    String       @id @default(cuid())
  tasks KanbanTask[]  // ✅ Relation inverse
}
```

**Résultat:** TypeScript + Runtime safe:
```typescript
// ✅ Type-safe et fonctionne
const column = await prisma.kanbanColumn.findUnique({
  where: { id: columnId },
  include: { tasks: true }  // ✓ TypeScript valide + runtime OK
})
```

**RÈGLE ABSOLUE:**
```
SI foreign key exists (columnId, userId, taskId, etc.)
ALORS relation MUST exist (column, user, task)
ET relation inverse MUST exist (tasks[], columns[], etc.)
```

---
  -h 89.116.27.88 \
  -p 5433 \
  -U pentester \
  -d postgres \
  -c "CREATE DATABASE nom_projet_db ENCODING 'UTF8';"
```

---

## Prisma Setup (Workflow Complet)

### Phase 1: DATABASE_URL Configuration

**Créer fichier `.env` avec DATABASE_URL:**

```bash
# Format DATABASE_URL
DATABASE_URL="postgresql://pentester:Voiture789@89.116.27.88:5433/nom_projet_db?schema=public"
```

**Breakdown:**
- `postgresql://` - Protocol
- `pentester` - User
- `Voiture789` - Password
- `89.116.27.88` - VPS IP
- `5433` - Port
- `nom_projet_db` - Database name (créée précédemment)
- `?schema=public` - PostgreSQL schema (défaut)

**Fichier .env complet:**
```env
# Database
DATABASE_URL="postgresql://pentester:Voiture789@89.116.27.88:5433/time_master_db?schema=public"

# Next.js
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="votre-secret-genere"
```

---

### Phase 2: Prisma Schema Generation

**Créer `prisma/schema.prisma` selon features projet:**

**Exemple: Dashboard Time Tracking + Tasks**

```prisma
// prisma/schema.prisma

generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// Models selon features demandées

model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  password  String   // Hashed
  role      Role     @default(USER)

  tasks     Task[]
  timeEntries TimeEntry[]

  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}

enum Role {
  USER
  ADMIN
}

model Task {
  id          String   @id @default(cuid())
  title       String
  description String?
  status      TaskStatus @default(TODO)
  priority    Priority   @default(MEDIUM)

  userId      String
  user        User     @relation(fields: [userId], references: [id], onDelete: Cascade)

  timeEntries TimeEntry[]

  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt

  @@index([userId])
}

enum TaskStatus {
  TODO
  IN_PROGRESS
  DONE
}

enum Priority {
  LOW
  MEDIUM
  HIGH
}

model TimeEntry {
  id        String   @id @default(cuid())
  startTime DateTime
  endTime   DateTime?
  duration  Int?     // Seconds

  taskId    String
  task      Task     @relation(fields: [taskId], references: [id], onDelete: Cascade)

  userId    String
  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)

  createdAt DateTime @default(now())

  @@index([taskId])
  @@index([userId])
}
```

**Adapter models selon features demandées:**
- Auth → Model User + Session
- Tasks → Model Task
- Time tracking → Model TimeEntry
- Categories → Model Category
- Tags → Model Tag
- Analytics → Pas de model (calculé depuis données existantes)

---

### Phase 3: Prisma Client Generation

```bash
# Install Prisma
npm install prisma @prisma/client

# Generate Prisma Client
npx prisma generate

echo "✅ Prisma Client généré"
```

---

### Phase 4: Database Push (Development)

**Pour développement (recommandé pour prototypes/MVP):**

```bash
# Push schema vers database (sans migrations)
npx prisma db push

# Résultat:
# - Crée tables dans PostgreSQL
# - Applique schema.prisma
# - Pas de fichiers migration

echo "✅ Schema pushed to database"
```

**OU Migrations (Production - plus strict):**

```bash
# Créer migration
npx prisma migrate dev --name init

# Résultat:
# - Crée prisma/migrations/
# - Applique migration
# - Historique migrations tracé

echo "✅ Migration init applied"
```

**Différence:**
- `db push` → Rapide, développement, pas d'historique
- `migrate dev` → Production-ready, historique, rollback possible

**Utiliser:** `db push` par défaut (sauf si user demande migrations explicitement)

---

### Phase 5: Prisma Client Singleton

**Créer `lib/prisma.ts` (évite multiple instances):**

```typescript
// lib/prisma.ts
import { PrismaClient } from '@prisma/client'

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined
}

export const prisma = globalForPrisma.prisma ?? new PrismaClient({
  log: process.env.NODE_ENV === 'development' ? ['query', 'error', 'warn'] : ['error'],
})

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma
```

**Usage dans API routes:**

```typescript
// app/api/tasks/route.ts
import { prisma } from '@/lib/prisma'

export async function GET() {
  const tasks = await prisma.task.findMany({
    include: { user: true }
  })
  return Response.json(tasks)
}
```

---

## Seeding Data (Données Test)

### Créer Script Seed

**`prisma/seed.ts`:**

```typescript
import { PrismaClient } from '@prisma/client'
import bcrypt from 'bcryptjs'

const prisma = new PrismaClient()

async function main() {
  console.log('🌱 Seeding database...')

  // Delete existing data
  await prisma.timeEntry.deleteMany()
  await prisma.task.deleteMany()
  await prisma.user.deleteMany()

  // Create admin user
  const adminPassword = await bcrypt.hash('admin123', 10)
  const admin = await prisma.user.create({
    data: {
      email: 'admin@example.com',
      name: 'Admin User',
      password: adminPassword,
      role: 'ADMIN',
    },
  })

  // Create test user
  const userPassword = await bcrypt.hash('user123', 10)
  const user = await prisma.user.create({
    data: {
      email: 'user@example.com',
      name: 'Test User',
      password: userPassword,
      role: 'USER',
    },
  })

  // Create sample tasks
  await prisma.task.createMany({
    data: [
      {
        title: 'Setup project',
        description: 'Initialize Next.js + Prisma',
        status: 'DONE',
        priority: 'HIGH',
        userId: admin.id,
      },
      {
        title: 'Build dashboard',
        description: 'Create admin dashboard UI',
        status: 'IN_PROGRESS',
        priority: 'HIGH',
        userId: admin.id,
      },
      {
        title: 'Write documentation',
        description: 'Document API endpoints',
        status: 'TODO',
        priority: 'MEDIUM',
        userId: user.id,
      },
    ],
  })

  console.log('✅ Database seeded!')
  console.log('📧 Admin: admin@example.com / admin123')
  console.log('📧 User: user@example.com / user123')
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
```

**Ajouter script dans `package.json`:**

```json
{
  "scripts": {
    "prisma:seed": "tsx prisma/seed.ts"
  },
  "prisma": {
    "seed": "tsx prisma/seed.ts"
  }
}
```

**Exécuter seed:**

```bash
# Install tsx (TypeScript executor)
npm install -D tsx

# Run seed
npm run prisma:seed

# Ou après migrate
npx prisma migrate reset --skip-seed
npx prisma db seed
```

---

## Prisma Studio (Database GUI)

**Lancer interface graphique Prisma:**

```bash
npx prisma studio

# Ouvre navigateur: http://localhost:5555
# Interface pour voir/éditer données directement
```

**Utile pour:**
- Vérifier données créées
- Debug relations
- Éditer manuellement
- Tester queries

---

## Troubleshooting Database

### Erreur: "Can't reach database server"

**Check:**
1. PostgreSQL VPS accessible?
   ```bash
   ping 89.116.27.88
   ```

2. Port 5433 ouvert?
   ```bash
   nc -zv 89.116.27.88 5433
   ```

3. Credentials corrects dans .env?
   ```bash
   cat .env | grep DATABASE_URL
   ```

---

### Erreur: "Database does not exist"

**Solution:**
```bash
# Créer database
PGPASSWORD="Voiture789" psql \
  -h 89.116.27.88 \
  -p 5433 \
  -U pentester \
  -d postgres \
  -c "CREATE DATABASE nom_projet_db;"

# Puis retry prisma db push
npx prisma db push
```

---

### Erreur: "Prisma schema mismatch"

**Solution:**
```bash
# Regenerate Prisma Client
npx prisma generate

# Reset database (DANGER - perte données)
npx prisma migrate reset

# Ou push nouveau schema
npx prisma db push --force-reset
```

---

## Backup & Restore Database

### Backup Database

```bash
# Dump database to SQL file
PGPASSWORD="Voiture789" pg_dump \
  -h 89.116.27.88 \
  -p 5433 \
  -U pentester \
  -d nom_projet_db \
  -F c \
  -f backup_$(date +%Y%m%d_%H%M%S).dump

echo "✅ Backup créé: backup_YYYYMMDD_HHMMSS.dump"
```

### Restore Database

```bash
# Restore from dump
PGPASSWORD="Voiture789" pg_restore \
  -h 89.116.27.88 \
  -p 5433 \
  -U pentester \
  -d nom_projet_db \
  -c \
  backup_20250111_143000.dump

echo "✅ Database restored"
```

---

## Best Practices

### 1. Naming Conventions

**Tables:** PascalCase singular
- ✅ `User`, `Task`, `TimeEntry`
- ❌ `users`, `Tasks`, `time_entries`

**Columns:** camelCase
- ✅ `createdAt`, `userId`, `startTime`
- ❌ `created_at`, `user_id`, `start_time`

**Enums:** UPPER_CASE
- ✅ `enum TaskStatus { TODO, IN_PROGRESS, DONE }`
- ❌ `enum TaskStatus { todo, inProgress, done }`

---

### 2. Relations & Indexes

**TOUJOURS:**
- `@@index` sur foreign keys
- `onDelete: Cascade` pour cleanup auto
- `@unique` sur emails/usernames

```prisma
model Task {
  userId String
  user   User @relation(fields: [userId], references: [id], onDelete: Cascade)

  @@index([userId])  // ✅ Performance query
}
```

---

### 3. Timestamps

**TOUJOURS ajouter:**
```prisma
createdAt DateTime @default(now())
updatedAt DateTime @updatedAt
```

---

### 4. IDs

**Préférer CUID sur UUID:**
```prisma
id String @id @default(cuid())  // ✅ Plus court, URL-friendly
```

---

## Workflow Complet Exemple

**User demande:** "Dashboard time tracking + tasks avec auth"

**EXECUTOR + skill database:**

```bash
# 1. Créer database
PGPASSWORD="Voiture789" psql -h 89.116.27.88 -p 5433 -U pentester -d postgres \
  -c "CREATE DATABASE time_tracker_db;"

# 2. Créer .env
cat > .env <<EOF
DATABASE_URL="postgresql://pentester:Voiture789@89.116.27.88:5433/time_tracker_db?schema=public"
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="$(openssl rand -base64 32)"
EOF

# 3. Créer prisma/schema.prisma (User, Task, TimeEntry models)

# 4. Install Prisma
npm install prisma @prisma/client

# 5. Generate client
npx prisma generate

# 6. Push schema
npx prisma db push

# 7. Créer lib/prisma.ts (singleton)

# 8. Seed données test
npm run prisma:seed

# Résultat:
# ✅ Database time_tracker_db créée
# ✅ Tables: User, Task, TimeEntry
# ✅ Données test (admin + user + 3 tasks)
# ✅ Ready pour API routes
```

---

## Conventions Non-Negotiables

1. **1 projet = 1 database** (isolation complète)
2. **Naming:** `[nom_projet]_db` (lowercase + underscore)
3. **Credentials VPS hardcodés** (89.116.27.88:5433)
4. **Prisma Client singleton** (lib/prisma.ts obligatoire)
5. **db push pour dev** (migrate dev si demandé explicitement)
6. **Indexes sur FK** (performance queries)
7. **Timestamps** (createdAt + updatedAt)
8. **Seeding données test** (facilite développement)

---

**Inspiré de:**
- Prisma Best Practices (prisma.io/docs)
- PostgreSQL Documentation (postgresql.org)
- Database-per-Service Pattern (microservices)
- Twelve-Factor App (database as resource)

---

**Version**: 1.0.0
**Last updated**: 2025-01-11
**Maintained by**: EXECUTOR agent

---

## 📋 EXEMPLE COMPLET: Projet avec Database

**Scenario:** User demande "Crée dashboard blog avec PostgreSQL"

### STEP 1: MCP Database Setup (5 secondes)

```typescript
// 1.1 Check databases existantes
const dbList = mcp__gestion__postgresql_list_databases()
// → 9 databases trouvées, pas de "blog_dashboard_db"

// 1.2 Créer database
const dbCreate = mcp__gestion__postgresql_create_database("blog_dashboard_db")
// → ✓ Database created: blog_dashboard_db (owner: pentester)

// 1.3 Obtenir DATABASE_URL
const dbUrl = mcp__gestion__postgresql_get_connection_url("blog_dashboard_db")
// → {
//     "url": "postgresql://pentester:Voiture789@89.116.27.88:5433/blog_dashboard_db",
//     "env_format": "DATABASE_URL=\"postgresql://pentester:Voiture789@89.116.27.88:5433/blog_dashboard_db\""
//   }

// 1.4 Écrire .env
Write(".env", `
DATABASE_URL="postgresql://pentester:Voiture789@89.116.27.88:5433/blog_dashboard_db"
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="$(openssl rand -base64 32)"
`)
```

**Résultat Phase 0:** ✅ Database créée + .env configuré (credentials garantis corrects)

---

### STEP 2: Prisma Schema (30 secondes)

```prisma
// prisma/schema.prisma

generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")  // ✅ Jamais hardcodé
}

// ✅ Relations bidirectionnelles OBLIGATOIRES
model Post {
  id          String    @id @default(cuid())
  title       String
  content     String
  published   Boolean   @default(false)
  authorId    String
  author      User      @relation(fields: [authorId], references: [id], onDelete: Cascade)
  categoryId  String
  category    Category  @relation(fields: [categoryId], references: [id])
  createdAt   DateTime  @default(now())
  updatedAt   DateTime  @updatedAt

  @@index([authorId])
  @@index([categoryId])
  @@index([published])
}

model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  posts     Post[]   // ✅ Relation inverse
  createdAt DateTime @default(now())
}

model Category {
  id    String @id @default(cuid())
  name  String @unique
  posts Post[] // ✅ Relation inverse
}
```

**Résultat Phase 1:** ✅ Schema écrit avec relations bidirectionnelles

---

### STEP 3: Validation Prisma (10 secondes)

```bash
# 3.1 Valider syntax
npm run prisma:validate
# → ✅ Schema is valid

# 3.2 Générer client
npm run prisma:generate
# → ✅ Generated Prisma Client

# 3.3 Check TypeScript (OBLIGATOIRE)
npm run typecheck
# → (vide = 0 errors) ✅

# 3.4 Push schema vers DB
npm run prisma:push
# → ✅ Your database is now in sync
```

**SI erreurs TypeScript détectées:**
```bash
npm run typecheck
# → error TS2339: Property 'author' does not exist

# FIX: Ajouter relation manquante dans schema.prisma
# Re-run validation complète
```

**Résultat Phase 2:** ✅ Schema validé + DB synchronisée (0 errors garantis)

---

### STEP 4: Vérification MCP (5 secondes)

```typescript
// Vérifier schema créé
const schema = mcp__gestion__postgresql_get_schema("blog_dashboard_db")
// → {
//     "tables": [
//       {"name": "Post", "columns": [...]},
//       {"name": "User", "columns": [...]},
//       {"name": "Category", "columns": [...]}
//     ],
//     "table_count": 3
//   }

// Vérifier connexion
const conn = mcp__gestion__postgresql_validate_connection("blog_dashboard_db")
// → {"connected": true, "version": "PostgreSQL 16.10"}
```

**Résultat Phase 3:** ✅ Database opérationnelle + tables créées

---

### STEP 5: Seed Data (optionnel, 10 secondes)

```typescript
// Utiliser MCP pour seed rapide
mcp__gestion__postgresql_insert_row("blog_dashboard_db", "User", {
  "email": "admin@blog.com",
  "name": "Admin"
})
// → {"inserted_row": {"id": "...", "email": "admin@blog.com", ...}}

mcp__gestion__postgresql_insert_row("blog_dashboard_db", "Category", {
  "name": "Technology"
})
// → {"inserted_row": {"id": "...", "name": "Technology"}}

// OU utiliser Prisma seed script (recommandé pour prod)
npm run prisma:seed
```

---

## ✅ Résultat Final

**Temps total:** ~60 secondes  
**Erreurs runtime:** 0 (détection compile-time)  
**Credentials:** Garantis corrects (MCP)  
**Relations:** Type-safe (bidirectionnelles)  
**Validation:** Automatique (prebuild hook)

**Database prête pour:**
- Server Actions CRUD
- API Routes
- Frontend components
- Production deployment

---

## 🚨 Erreurs Courantes Évitées

**Sans MCP Workflow:**
```bash
# ❌ Credentials incorrects
DATABASE_URL="postgresql://pilote:xxx@localhost:5434/..."
# → Runtime error: Authentication failed

# ❌ Relations manquantes
model Post {
  authorId String  // Pas de relation
}
# → Runtime error: Property 'author' does not exist

# ❌ Skip validation
npx prisma db push  // Direct sans typecheck
# → Build errors découverts tard
```

**Avec MCP Workflow:**
```typescript
// ✅ Credentials garantis
mcp__gestion__postgresql_get_connection_url("...")
// → postgresql://pentester:Voiture789@89.116.27.88:5433/...

// ✅ Relations forcées
model Post {
  authorId String
  author   User @relation(...)  // Obligatoire
}

// ✅ Validation automatique
npm run validate  // Avant build
# → 0 errors ou STOP
```

---

**Version:** 2.0.0 (MCP Integration)  
**Last updated:** 2025-01-12  
**Maintained by:** EXECUTOR agent + MCP gestion

