---
name: laravel-scaffold-basico
description: "Use quando precisar criar migration, rodar migrate, gerar seeder, model e controller via comandos artisan padronizados."
---

# Skill: Scaffold Basico Laravel

## Objetivo
Padronizar criacao de artefatos do Laravel via `php artisan`, evitando criacao manual de arquivos.

## Regras
- Sempre criar migration com comando Artisan.
- Sempre rodar migrations apos criar/ajustar a migration.
- Sempre criar seeder com comando Artisan.
- Sempre criar model com comando Artisan.
- Sempre criar controller com comando Artisan.

## Comandos Padrao

### 1. Criar migration
```bash
php artisan make:migration nome_da_migration
```

### 2. Rodar migrations
```bash
php artisan migrate
```

### 3. Criar seeder
```bash
php artisan make:seeder NomeDaSeeder
```

### 4. Criar model
```bash
php artisan make:model NomeDoModel
```

### 5. Criar controller
```bash
php artisan make:controller NomeDoController
```

## Observacoes
- Use `PascalCase` para `Seeder`, `Model` e `Controller`.
- Use nomes descritivos em migrations (ex.: `create_products_table`, `add_status_to_orders_table`).
