---
name: observability-architecture
description: Наблюдаемость: логи/метрики/трейсы, корреляция, алерты, SLI.
version: 1.0
lastUpdated: 2026-02-04
---

# Observability Architecture (Skill)

## Когда применять

- Определяем обязательные поля логов и корреляцию
- Проектируем метрики и SLI для SLO
- Настраиваем алертинг по деградациям

## Правила

- Логи JSON, поля: `correlationId`, `tenantId`.
- Метрики: `/metrics` для каждого сервиса, p95/p99 латентности.
- Трейсы: OpenTelemetry, связка по `correlationId`.
- Health: `/health`, `/ready`.
- Алерты: ошибка/латентность/очереди/лаг как отдельные сигналы.
