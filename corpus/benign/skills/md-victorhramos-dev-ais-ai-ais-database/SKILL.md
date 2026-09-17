---
name: ais-database
description: Schema PostgreSQL e migrations para o sistema AIS. Use quando criar tabelas, migrations, índices ou trabalhar com particionamento temporal.
license: MIT
compatibility: opencode
metadata:
  database: postgresql
  orm: eloquent
  domain: ais-maritime
---

# AIS Database Schema & Migrations

PostgreSQL 15+ com particionamento temporal e conexão dedicada 'ais'.

## Tabelas Principais

### ais_messages (Particionada por mês)

```sql
CREATE TABLE ais_messages (
    id BIGSERIAL,
    mmsi VARCHAR(9) NOT NULL,
    message_type SMALLINT NOT NULL,
    raw_nmea TEXT NOT NULL,
    nmea_checksum VARCHAR(4),
    source_id VARCHAR(50),
    parsed_data JSONB,
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    speed_over_ground DECIMAL(5,1),
    course_over_ground DECIMAL(5,1),
    true_heading SMALLINT,
    navigation_status SMALLINT,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    antenna_id INTEGER,
    dedup_hash VARCHAR(64) NOT NULL,
    PRIMARY KEY (id, received_at)
) PARTITION BY RANGE (received_at);
```

### vessels (Cache de navios)

```sql
CREATE TABLE vessels (
    id SERIAL PRIMARY KEY,
    mmsi VARCHAR(9) UNIQUE NOT NULL,
    name VARCHAR(127),
    imo VARCHAR(10),
    callsign VARCHAR(20),
    ship_type SMALLINT,
    length SMALLINT,
    width SMALLINT,
    draught DECIMAL(4,1),
    destination VARCHAR(127),
    eta TIMESTAMPTZ,
    last_position_at TIMESTAMPTZ,
    last_static_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### analysis_summaries

```sql
CREATE TABLE analysis_summaries (
    id SERIAL PRIMARY KEY,
    trigger_type VARCHAR(20) NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    messages_analyzed INTEGER NOT NULL,
    vessels_unique INTEGER NOT NULL,
    summary_text TEXT NOT NULL,
    key_events JSONB,
    risk_level VARCHAR(10),
    llm_model VARCHAR(50),
    tokens_used INTEGER,
    latency_ms INTEGER,
    generated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Migrations Laravel

### Estrutura Padrão

```php
<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    protected $connection = 'ais';

    public function up(): void
    {
        // Usar raw SQL para features PostgreSQL avançadas
        DB::connection('ais')->statement('
            CREATE TABLE IF NOT EXISTS nome_tabela (
                -- definição
            )
        ');
    }

    public function down(): void
    {
        Schema::connection('ais')->dropIfExists('nome_tabela');
    }
};
```

### Particionamento Mensal

```php
// Criar partição para o mês atual
$mesAtual = now()->format('Y_m');
$inicioMes = now()->startOfMonth()->toDateTimeString();
$fimMes = now()->endOfMonth()->addSecond()->toDateTimeString();

DB::connection('ais')->statement("
    CREATE TABLE IF NOT EXISTS ais_messages_{$mesAtual}
    PARTITION OF ais_messages
    FOR VALUES FROM ('{$inicioMes}') TO ('{$fimMes}')
");
```

## Índices Críticos

```sql
-- Performance de queries por MMSI
CREATE INDEX idx_ais_messages_mmsi ON ais_messages(mmsi);

-- Performance de queries por tipo
CREATE INDEX idx_ais_messages_type ON ais_messages(message_type);

-- Performance de queries temporais
CREATE INDEX idx_ais_messages_received ON ais_messages(received_at DESC);

-- Deduplicação (único por hash + janela temporal)
CREATE UNIQUE INDEX idx_ais_messages_dedup 
ON ais_messages(dedup_hash, received_at);

-- Vessels por MMSI (lookup rápido)
CREATE UNIQUE INDEX idx_vessels_mmsi ON vessels(mmsi);

-- Vessels por nome (busca textual)
CREATE INDEX idx_vessels_name ON vessels(name);
```

## Conexão Dedicada

```php
// config/database.php
'ais' => [
    'driver' => 'pgsql',
    'host' => env('AIS_DB_HOST', '127.0.0.1'),
    'port' => env('AIS_DB_PORT', '5432'),
    'database' => env('AIS_DB_DATABASE', 'ais_system'),
    'username' => env('AIS_DB_USERNAME', 'ais_user'),
    'password' => env('AIS_DB_PASSWORD', ''),
    'charset' => 'utf8',
    'prefix' => '',
    'schema' => 'public',
],
```

## Regras

- SEMPRE usar conexão 'ais' para tabelas AIS
- NUNCA modificar migrations existentes (criar novas)
- SEMPRE criar índices para colunas usadas em WHERE/JOIN
- Partições mensais para ais_messages (retenção 12 meses)
- Usar JSONB para dados semi-estruturados (parsed_data)

## Referências

- @.docs/SPEC-01: Database Schema & Migrations.md para detalhes completos
