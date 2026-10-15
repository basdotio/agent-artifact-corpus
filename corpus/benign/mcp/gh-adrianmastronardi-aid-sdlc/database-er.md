# Database Entidad-Relación

## Propósito y alcance

Representar **visualmente** el modelo de datos del proyecto, incluyendo entidades/colecciones,
cardinalidades y reglas de integridad, en formato **Mermaid** para consumo humano y de copilotos.
Este documento es la fuente de verdad de relaciones y debe actualizarse **antes** de modificar
esquemas o migraciones.

---

## Diagrama ER (bases relacionales)

```mermaid
erDiagram
    USERS {
      uuid id PK
      text email "UNIQUE, PII:HIGH"
      boolean is_active "DEFAULT true"
      timestamptz created_at
      timestamptz updated_at
    }

    ADDRESSES {
      uuid id PK
      uuid user_id FK
      text line1
      text line2
      text city
      text state
      text postal_code
      text country
      timestamptz created_at
      timestamptz updated_at
    }

    PRODUCTS {
      uuid id PK
      text sku "UNIQUE"
      text name
      numeric price "scale/precision definido"
      boolean is_active
      timestamptz created_at
      timestamptz updated_at
    }

    ORDERS {
      uuid id PK
      uuid user_id FK
      uuid shipping_address_id FK
      text status
      timestamptz placed_at
      timestamptz created_at
      timestamptz updated_at
    }

    ORDER_ITEMS {
      uuid id PK
      uuid order_id FK
      uuid product_id FK
      integer quantity
      numeric unit_price
      timestamptz created_at
      timestamptz updated_at
    }

    PAYMENTS {
      uuid id PK
      uuid order_id FK
      text provider
      text provider_ref "tokenizado si aplica"
      numeric amount
      text status
      timestamptz paid_at
      timestamptz created_at
      timestamptz updated_at
    }

    USERS ||--o{ ADDRESSES : "has"
    USERS ||--o{ ORDERS : "places"
    ORDERS ||--|{ ORDER_ITEMS : "contains"
    PRODUCTS ||--o{ ORDER_ITEMS : "in"
    ORDERS ||--o{ PAYMENTS : "has"
    ADDRESSES ||--o{ ORDERS : "used_as_shipping"
```

---

## Claves foráneas y reglas de integridad

| Tabla       | Columna FK          | Referencia   | ON DELETE | ON UPDATE | Índice sugerido                  | Justificación                                                       |
| ----------- | ------------------- | ------------ | --------- | --------- | -------------------------------- | ------------------------------------------------------------------- |
| orders      | user_id             | users.id     | RESTRICT  | CASCADE   | `orders_user_id_idx`             | Prohibir eliminar usuarios con historial por auditoría/facturación. |
| orders      | shipping_address_id | addresses.id | SET NULL  | CASCADE   | `orders_shipping_address_id_idx` | Preservar órdenes si se depuran direcciones; mantener trazabilidad. |
| order_items | order_id            | orders.id    | CASCADE   | CASCADE   | `order_items_order_id_idx`       | Limpiar items dependientes al eliminar el pedido.                   |
| order_items | product_id          | products.id  | RESTRICT  | CASCADE   | `order_items_product_id_idx`     | Mantener trazabilidad de catálogo en historial de ventas.           |
| payments    | order_id            | orders.id    | CASCADE   | CASCADE   | `payments_order_id_idx`          | Un pago no tiene sentido sin el pedido asociado.                    |

---

## Overlay de PII y datos sensibles

| Entidad   | Atributo            | PII      | Protección requerida               |
| --------- | ------------------- | -------- | ---------------------------------- |
| users     | email               | HIGH     | Hash/enmascarado                   |
| orders    | shipping_address_id | INDIRECT | Redactar parcialmente              |
| addresses | line1/line2/...     | MODERATE | Enmascarar; nunca en logs públicos |
| payments  | provider_ref        | MODERATE | Tokenización                       |

---

## Estructuras no relacionales (visualización)

Para colecciones/documentos, usa vistas Mermaid que ilustren **estructura**, **anidamiento** y
**referencias lógicas**.

### customers (MongoDB) – estructura documental

```mermaid
classDiagram
  class customers {
    ObjectId _id
    string name
    string email  // pattern: ^.+@.+$  (PII: HIGH)
    ObjectId[] purchases  // refs a orders.id
  }
```

### Relación lógica documentos ↔ relacional

```mermaid
flowchart LR
  C[customers._id] -->|"purchases[] (array de refs)"| O[(orders.id)]
  O -->|"order_id (FK)"| I[(order_items.id)]
  I -->|"product_id (FK)"| P[(products.id)]
```

### ER NoSQL anotado (embedded vs. referenced vs. denorm)

**Convención de tags**:

- `[embedded]` documento embebido
- `[referenced]` referencia por id (lookup)
- `[denorm]` denormalización para lectura rápida

```mermaid
erDiagram
  %% Contexto NoSQL (MongoDB)
  %% Las relaciones documentales se modelan con fields anotados

  CUSTOMERS ||--o{ ORDERS : "referenced via orders.customer_id"
  ORDERS   ||--|{ ORDER_ITEMS : "embedded OR referenced (ver campos)"
  ORDER_ITEMS }o--|| PRODUCTS : "referenced via product_id"

  CUSTOMERS {
    objectId _id PK
    string   name
    string   email "PII:HIGH"
  }

  ORDERS {
    objectId _id PK
    objectId customer_id  "[referenced] CUSTOMERS._id"
    object   shipping_address "[embedded]"
    array    items_ids "[denorm] ORDER_ITEMS._id (si no se embebe)"
    timestamptz created_at
  }

  ORDER_ITEMS {
    objectId _id PK
    objectId order_id   "[referenced] ORDERS._id (si no se embebe)"
    object   item       "[embedded] { product_id, qty, unit_price }"
    objectId product_id "[referenced] PRODUCTS._id"
  }

  PRODUCTS {
    objectId _id PK
    string   sku "UNIQUE"
    string   name
    numeric  price
  }
```

---

## Reglas de actualización del ER

1. **Primero aquí, luego código y migraciones**: cualquier cambio de relación se documenta primero
   en `database.md` (detalle estructural) y `database-er.md` (diagrama). Luego se implementa el
   cambio en el código de la aplicación (modelos, repositorios, APIs) y, por último, se crea y
   ejecuta la **migración de base de datos** correspondiente —es decir, el script que aplica esos
   cambios en el esquema real (crear/alterar/eliminar tablas, columnas, índices o relaciones).
1. **Compatibilidad con copilotos**: describir propósito y relaciones en texto breve junto al
   diagrama para reducir ambigüedad.
1. **Convenciones**: `snake_case`, PK `id`, FKs `<entidad>_id`, `created_at`/`updated_at` UTC.
1. **Formato Markdown**: seguir `markdown-guidelines.md` (encabezados ATX, tablas estándar, fences
   con lenguaje).

---

## Checklist para PRs que tocan datos

- [ ] Diagrama Mermaid actualizado y válido.
- [ ] Relaciones del diagrama **etiquetadas con la columna FK** y comentario `%%` con ON
      DELETE/UPDATE.
- [ ] Tabla de FKs actualizada con columna **Justificación** por cada regla.
- [ ] Migración alineada al orden: docs (`database.md` + `database-er.md`) → **código**
      (modelos/repositorios/APIs) → **migración**.
- [ ] Overlay PII revisado (campos nuevos rotulados y con controles).
- [ ] Migración con ruta **aditiva → backfill → switch de código → limpieza** y rollback definido.
- [ ] Linters/validadores de `database.md` y `database-er.md` en pre-commit/CI pasan sin warnings.
