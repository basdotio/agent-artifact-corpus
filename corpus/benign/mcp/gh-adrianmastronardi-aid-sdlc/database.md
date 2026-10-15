# Database

## Propósito

Definir y documentar las estructuras de datos persistentes utilizadas por este proyecto, incluyendo
campos, tipos, relaciones y convenciones de modelado, de forma que tanto personas como copilotos de
IA puedan comprender y trabajar con el modelo de datos de manera precisa y segura.

---

## Alcance

Este documento cubre todas las bases de datos y sistemas de almacenamiento persistente asociados al
proyecto (relacionales, no relacionales o especializadas) en todos los entornos (desarrollo,
staging, producción). Incluye referencias a diagramas y documentación técnica en
[`database-er.md`](database-er.md) y establece la clasificación y manejo de datos sensibles según lo
definido en [`security.md`](security.md).

---

## Convenciones de modelado

Las siguientes convenciones son obligatorias para todos los modelos de datos del proyecto:

- **Naming**
  - Entidades (tablas) y colecciones: `snake_case` en inglés.
  - Campos: `snake_case` en inglés, sin abreviaturas ambiguas.
  - Claves primarias: `id` o `<entidad>_id`.
  - Claves foráneas: `<entidad>_id` con relación explícita documentada (ver sección
    [Relaciones](#relaciones)).

- **Tipado**
  - Usar tipos nativos del motor siempre que sea posible.
  - Especificar tamaño/precisión en campos numéricos y de texto.
  - Booleanos prefijados con `is_` o `has_`.

- **Fechas y horas**
  - Formato UTC siempre.
  - Campos estándar: `created_at`, `updated_at`.

- **Integridad y relaciones**
  - Definir PK y FK explícitas.
  - Documentar reglas ON DELETE/UPDATE.

- **PII y datos sensibles**
  - Declarar en sección 4 y seguir [`security.md`](security.md).

- **Indexación**
  - Nombres `<tabla>_<columna>_idx`.
  - Justificar índices no estándar.

- **Compatibilidad con copilotos**
  - Descripción funcional de cada entidad/colección y campo.
  - Evitar abreviaturas no documentadas.

---

## Gestión de datos sensibles y PII

Esta sección es **obligatoria** y estandarizada para todos los proyectos. Define cómo identificar,
clasificar y proteger PII y otros datos sensibles, en línea con [`security.md`](security.md). Toda
columna/atributo que contenga PII **debe** declararse aquí; su ausencia se interpreta como
incumplimiento.

### Principios obligatorios

- **Mínimo privilegio y segregación de roles**: permisos acotados por componente (aplicación, jobs,
  BI) y separación estricta de cuentas humanas y de servicio.
- **Cifrado**: en tránsito (TLS 1.2+ como mínimo) y en reposo (KMS/CMEK o equivalente según el
  motor/plataforma).
- **No exposición**: prohibido incluir PII en logs, mensajes de error o respuestas de API;
  sanitizar/anonimizar antes de enviar a servicios externos.
- **Secretos**: credenciales y materiales criptográficos fuera del código y de la documentación;
  gestionar vía Secret Manager/variables de entorno con rotación.
- **Validación y sanitización**: listas blancas de formato, límites de tamaño y
  escape/parametrización en todos los sinks (SQL/HTML/JSON/XML).

### Clasificación e inventario PII

- Etiquetar cada atributo sensible con `PII: {NONE|LOW|MODERATE|HIGH}` y, si aplica, `CONFIDENTIAL`.
- Mantener el siguiente inventario actualizado; si el sistema no maneja PII, declarar
  explícitamente: “Este sistema no almacena PII.”

| Entidad/Colección | Atributo         | Tipo      | PII      | Protección aplicada                  | Acceso (rol)      | Justificación de negocio |
| ----------------- | ---------------- | --------- | -------- | ------------------------------------ | ----------------- | ------------------------ |
| users             | email            | text      | HIGH     | Hash/enmascarado en vistas           | app-read, bi-read | Contacto del usuario     |
| users             | phone_number     | text      | HIGH     | Tokenización + validación de formato | app-read          | Notificaciones           |
| orders            | shipping_address | json/text | MODERATE | Redacción parcial en logs            | app-read          | Envíos                   |

**Ejemplos de casos de uso:**

- **Email (users.email)**: debe ser hasheado antes de enviarse a sistemas de BI para proteger la
  identidad del usuario, manteniendo la capacidad de unir registros de forma no reversible.
- **Dirección de envío (orders.shipping_address)**: enmascarar parcialmente (p. ej., ocultar número
  de calle) en logs para diagnósticos, pero mantener completa para integraciones con servicios de
  envíos.

Estos ejemplos sirven como referencia para que desarrolladores y copilotos apliquen las técnicas de
protección adecuadas en situaciones concretas, comprendiendo los matices entre seguridad y
funcionalidad.

### Técnicas de protección requeridas

- **Mascaramiento/Tokenización** en datasets analíticos y vistas públicas; **hash con salt** donde
  corresponda (identificadores sensibles).
- **Retención y minimización**: almacenar solo lo necesario, con políticas de TTL/archivo
  documentadas en la sección de particionamiento/retención del documento.
- **Consultas y logs**: parametrización obligatoria; prohibido registrar parámetros/valores de PII
  en trazas o métricas.

### Accesos y auditoría

- Publicar matriz de roles → permisos efectivos por entidad/columna sensible; accesos auditables y
  revisiones periódicas.
- Cualquier incidente o sospecha de exposición activa el procedimiento de respuesta en < 30 minutos
  (ver [`security.md`](security.md)).

---

## Tablas y estructuras

Esta sección describe las entidades (bases relacionales) y colecciones (bases no relacionales) u
otras estructuras de almacenamiento persistente del proyecto.

**Nota de formato para descripciones funcionales:** Las descripciones funcionales de entidades y
campos deben seguir un formato estructurado para maximizar la comprensión por parte de la IA y
permitir la extracción automática de relaciones y propósitos.  
Formato recomendado:  
`[Propósito]: ... [Relaciones]: ...`

**Ejemplo:**
`[Propósito]: Almacena datos de usuarios registrados. [Relaciones]: Se relaciona con 'orders' y 'addresses'.`

### Bases relacionales

Para cada entidad:

1. **Nombre**.
2. **Descripción funcional** breve.
3. Tabla con definición de columnas/campos.

**Ejemplo:**

```markdown
### users

**Descripción funcional:** Almacena datos de usuarios registrados.

| Columna / Campo | Tipo de dato | Nulo | PK  | FK  | Índices          | Restricciones / Reglas de negocio |
| --------------- | ------------ | ---- | --- | --- | ---------------- | --------------------------------- |
| id              | uuid         | no   | sí  | –   | pk_users         | Inmutable                         |
| email           | text         | no   | –   | –   | uq_users_email   | Único global                      |
| is_active       | boolean      | no   | –   | –   | idx_users_active | Default `true`                    |
```

### Bases no relacionales

Para cada colección:

1. **Nombre**.
2. **Descripción funcional** breve.
3. Ejemplo de documento JSON con anotaciones de tipos y validaciones.

**Ejemplo:**

```markdown
### customers (MongoDB)

**Descripción funcional:** Almacena información de clientes y su historial de compras.
```

**Esquema esperado (JSON Schema simplificado):**

```json
{
  "bsonType": "object",
  "required": ["_id", "name", "email"],
  "properties": {
    "_id": { "bsonType": "objectId" },
    "name": { "bsonType": "string", "description": "Nombre completo" },
    "email": { "bsonType": "string", "pattern": "^.+@.+$" },
    "purchases": {
      "bsonType": "array",
      "items": { "bsonType": "objectId", "description": "ID de orden en 'orders'" }
    }
  }
}
```

**Notas:**

- Indexar `email` como único.
- Validar formato de correo en la capa de aplicación.
- Definir tamaño máximo de arrays de `purchases` si aplica.

### Notas sobre índices y claves

- Usar convención de nombres definida en [Convenciones de modelado](#convenciones-de-modelado).
- Documentar propósito de índices no evidentes.
- Indicar si la PK es simple o compuesta.

### Ejemplos de consultas o documentos

```sql
SELECT id, email FROM users WHERE is_active = true;
```

```json
{
  "id": "uuid",
  "email": "usuario@example.com",
  "is_active": true
}
```

---

## Relaciones

Las relaciones entre entidades están documentadas y mantenidas en
[`database-er.md`](database-er.md).  
Este documento incluye:

- Diagramas entidad–relación actualizados.
- Definición de cardinalidades (1:1, 1:N, N:M).
- Lista de claves foráneas, reglas `ON DELETE` / `ON UPDATE` y restricciones de integridad.
- Mapeo de referencias explícitas o embeddings en bases no relacionales.

**Nota:** Cualquier cambio en el modelo de datos que afecte relaciones debe reflejarse primero en
`database-er.md` antes de actualizar este documento.

---

## Procedimientos y operaciones críticas

Esta sección documenta las operaciones clave que deben seguirse para mantener la disponibilidad,
integridad y seguridad de las bases de datos del proyecto.

### Migraciones de esquema

Esta subsección documenta el proceso para modificar la estructura de la base de datos de forma
controlada, asegurando compatibilidad con el código y minimizando riesgos en entornos productivos.

**Elementos obligatorios:**

- **Herramienta utilizada**: especificar (ej. Alembic, Django Migrations) y enlace a la
  configuración o manual interno.
- **Flujo estándar**:
  1. Desarrollo y validación local.
  1. Prueba en entorno de staging con datos representativos.
  1. Ejecución programada en producción.
- **Patrón para cambios breaking**:
  - **Ruta aditiva**: agregar la nueva estructura sin eliminar la anterior.
  - **Backfill**: migrar datos antiguos a la nueva estructura.
  - **Migración de código**: actualizar la aplicación para que use la nueva estructura.
  - **Eliminación**: retirar la estructura anterior una vez confirmada su inutilización.
- **Rollback documentado**: para cada migración crítica, definir pasos claros para revertir el
  cambio.
- **Validaciones post-migración**: pruebas de integridad y funcionamiento mínimo tras aplicar el
  cambio.
- **Registro y trazabilidad**: ubicación donde quedan los scripts, logs y evidencias de ejecución.

**Nota AI-Driven SDLC:** Estructurar esta información permite que el copiloto:

1. Genere scripts de migración compatibles con la herramienta definida.
1. Automatice el patrón de cambios breaking para evitar interrupciones de servicio.
1. Proponga validaciones y pruebas adaptadas al modelo de datos.
1. Detecte dependencias en el código que puedan verse afectadas y sugiera actualizaciones.

### Backups y restauración

Este apartado documenta cómo se asegura la recuperación de datos en caso de pérdida, corrupción o
incidente, optimizando la capacidad de respuesta tanto de personas como de copilotos.

**Elementos obligatorios:**

- **Frecuencia y tipo de backups**: especificar si son completos (_full_), incrementales,
  diferenciales o con recuperación a un punto en el tiempo (_PITR_).
- **Ubicación y almacenamiento**: on-premises, cloud, tipo de cifrado (KMS, CMEK u otro),
  redundancia geográfica.
- **Procedimiento de restauración**: pasos detallados, incluyendo comandos, scripts y validaciones
  post-restauración. Debe estar probado en un entorno de staging y validado como funcional.
- **Verificación asistida por IA**: descripción de cómo el copiloto puede generar o ejecutar scripts
  de validación, comparar integridad y detectar discrepancias.
- **Roles responsables**:
  - **Ejecución**: rol encargado de iniciar el proceso (ej. _DBA on call_, _SRE de guardia_).
  - **Verificación**: rol que valida integridad y consistencia de datos restaurados.
  - **Registro de evidencia**: repositorio o sistema donde se documenta la restauración, los
    resultados y cualquier anomalía.
- **Pruebas periódicas**: frecuencia y metodología de las restauraciones de prueba para garantizar
  que los backups son utilizables.

**Nota AI-Driven SDLC:** Documentar estos elementos permite que el copiloto:

1. Sugerir scripts de restauración adaptados al motor y formato de backup.
1. Automatizar pruebas de integridad en restauraciones de staging.
1. Generar reportes de cumplimiento y trazabilidad para auditorías.

### Archivado y retención de datos

Esta sección define las políticas y procesos para almacenar, minimizar y eliminar datos de forma
segura, cumpliendo regulaciones y maximizando la eficiencia operativa.

**Elementos obligatorios:**

- **Políticas de retención por entidad**: definir, para cada tabla/colección, el tiempo que los
  datos deben mantenerse antes de ser archivados o eliminados (ej. 90 días, 5 años).
- **Criterios de archivado**: reglas para decidir cuándo un dato pasa de almacenamiento activo a
  archivado (por fecha, estado, inactividad, etc.).
- **Formatos y ubicación de archivo**: tipo de archivo (CSV, Parquet, JSON, binario), ubicación
  (on-prem, cloud), cifrado y redundancia.
- **Borrado seguro**: método aplicado (wipe, crypto-shred, sobrescritura múltiple), con referencia a
  normativas aplicables (GDPR, Ley de Habeas Data, HIPAA).
- **Cumplimiento normativo**: enlace a requisitos legales/regulatorios relevantes y cómo se asegura
  su cumplimiento en cada proceso de archivado/eliminación.
- **Roles responsables**:
  - **Ejecución**: quién realiza el proceso de archivado/borrado.
  - **Verificación**: quién valida que se cumplieron los plazos y se aplicó el método correcto.
  - **Registro de evidencia**: dónde queda documentado (logs, tickets, reportes).
- **Automatización y copiloto**:
  - Scripts o consultas que el copiloto puede generar para detectar datos candidatos a archivado
    según las políticas.
  - Validaciones automáticas para confirmar que se cumplieron plazos y métodos.
  - Reportes generados por IA para auditorías y seguimiento.

**Nota AI-Driven SDLC:** Mantener esta información estructurada permite al copiloto:

1. Identificar y proponer conjuntos de datos para archivado.
1. Ejecutar scripts seguros de borrado en entornos controlados.
1. Verificar que las políticas de retención se cumplen de forma continua y trazable.

### Rotación de claves y credenciales

Esta sección documenta los procedimientos para cambiar de forma segura contraseñas, claves API,
certificados y materiales criptográficos, garantizando continuidad operativa y minimizando riesgo de
exposición.

**Elementos obligatorios:**

- **Alcance**:
  - Tipos de secretos cubiertos: contraseñas de base de datos, claves API, certificados TLS, claves
    de cifrado, tokens de acceso.
  - Sistemas o entornos afectados (desarrollo, staging, producción).
- **Frecuencia**:
  - Intervalo de rotación recomendado por tipo de secreto (ej. 90 días para contraseñas DB, 1 año
    para certificados TLS).
  - Eventos que obligan a rotación inmediata (compromiso, fuga de credenciales, cambio de
    proveedor).
- **Procedimiento de rotación**:
  1. Generar nuevo secreto (usando herramienta aprobada, ej. Vault, AWS Secrets Manager, Azure Key
     Vault).
  1. Actualizar configuración en todos los sistemas que lo utilizan.
  1. Validar conectividad y funcionamiento tras el cambio.
  1. Revocar/eliminar el secreto anterior.
- **Gestión segura**:
  - Prohibido almacenar secretos en código, repositorios o documentación en texto plano.
  - Uso obligatorio de gestores de secretos y variables de entorno.
- **Roles responsables**:
  - **Ejecución**: rol que realiza la rotación.
  - **Verificación**: rol que valida que el nuevo secreto funciona y el anterior fue eliminado.
  - **Registro**: sistema/ticket/log donde se documenta el cambio y la verificación.
- **Automatización y copiloto**:
  - Scripts de actualización masiva generados por IA para entornos de prueba.
  - Validaciones automáticas para confirmar que no queda rastro del secreto anterior.
  - Generación de reportes de rotación para auditorías.

**Nota AI-Driven SDLC:** Documentar este flujo permite al copiloto:

1. Asistir en la generación y despliegue seguro de nuevos secretos.
1. Automatizar pruebas post-rotación para detectar fallos antes de que impacten en producción.
1. Reducir el tiempo de respuesta ante incidentes de seguridad relacionados con credenciales.

### Procedimiento ante incidentes

Esta sección describe los pasos a seguir ante eventos que comprometan la disponibilidad, integridad
o confidencialidad de los datos, integrando la respuesta humana con la asistencia de copilotos.

**Elementos obligatorios:**

- **Definición de incidente**: pérdida o corrupción de datos, intrusión, fuga de información, fallo
  de hardware, error humano crítico.
- **Detección**:
  - Fuentes: monitoreo, alertas de seguridad, reportes de usuarios.
  - Rol responsable de validar la alerta.
- **Respuesta inmediata**:
  1. Aislar el sistema afectado para evitar propagación.
  1. Notificar a los roles definidos en `security.md`.
  1. Iniciar registro de evidencias (logs, capturas, timestamps).
- **Acciones correctivas**:
  - Restauración desde backups.
  - Aplicación de parches o cambios de configuración.
  - Rotación de credenciales si procede.
- **Automatización y copiloto**:
  - Generación de checklist de respuesta según tipo de incidente.
  - Extracción automática de logs y métricas relevantes.
  - Generación de reportes post-incident.
- **Comunicación**:
  - Canales oficiales y responsables de informar internamente y a terceros (clientes, reguladores).
- **Cierre y lecciones aprendidas**:
  - Documentar causas, impacto, acciones tomadas y mejoras para prevenir recurrencia.

**Nota AI-Driven SDLC:** Documentar el flujo permite que el copiloto pueda guiar al equipo paso a
paso durante un incidente, proponer acciones basadas en casos previos registrados y, adicionalmente:

- Analizar patrones en los datos y logs recopilados para sugerir una posible causa raíz inicial.
- Priorizar hipótesis de resolución basadas en incidentes similares.
- Generar un resumen estructurado del incidente (impacto, causas probables, acciones en curso) para
  comunicación interna y externa.

Esto permite reducir el tiempo hasta la primera hipótesis y mejorar la calidad de la respuesta
inicial.

### Validaciones post-operación

Esta sección define cómo confirmar que una operación crítica (migración, restauración, rotación de
claves, borrado de datos) se ejecutó correctamente y que el sistema está en un estado estable.

**Elementos obligatorios:**

- **Tipos de validaciones**:
  - Pruebas de integridad de datos (checksums, conteo de registros).
  - Pruebas funcionales mínimas (consultas clave, endpoints críticos).
  - Monitoreo de rendimiento posterior al cambio.
- **Herramientas**:
  - Scripts de verificación, suites de pruebas automatizadas, dashboards de observabilidad.
- **Responsables**:
  - Rol que ejecuta las validaciones.
  - Rol que aprueba el resultado y cierra la operación.
- **Registro**:
  - Ubicación donde se almacenan resultados, logs y evidencias.
- **Automatización y copiloto**:
  - Ejecución de pruebas automatizadas según el tipo de operación.
  - Comparación de métricas pre y post-operación.
  - Generación de reportes para documentar que la operación fue exitosa.

**Nota AI-Driven SDLC:** Mantener esta sección detallada permite que el copiloto ejecute
validaciones predefinidas de forma autónoma y alerte al equipo si detecta desviaciones.

---

## Rendimiento e indexación

Esta sección define cómo medimos, optimizamos y controlamos el rendimiento del modelo de datos. Su
objetivo es que humanos y copilotos puedan identificar cuellos de botella, proponer índices/cambios
seguros y verificar mejoras.

### Consultas críticas y SLO/SLAs

- **Listado de consultas/endpoints críticos** con su propósito.
- **Objetivos** de latencia (p95/p99), throughput y tasa de errores.
- **Dataset representativo** (tamaño, cardinalidades, distribución).

### Estrategia de indexación

- Convenciones de nombre: `ix_<tabla>_<col1>_<col2>`, `uq_<tabla>_<col>`.
- **Índices compuestos** (orden por selectividad/uso), **cubrientes** y **parciales**.
- Texto/JSON: GIN/GIST (si el motor lo soporta) y campos indexables explícitos.
- Documentar el **propósito** de cada índice no trivial y su consulta objetivo.
- **Ciclo de vida** del índice: creación, validación de beneficio, eliminación si queda obsoleto.

### Particionamiento y sharding

- Estrategia (por rango/clave/fecha) y **clave de partición/shard**.
- Límites de tamaño por partición y rotación/archivado.
- Gestión de **particiones calientes** y rebalancing.

### Materializaciones y caché

- Vistas materializadas: fuente, **política de refresh** (cron/trigger/on‑demand).
- Caché (ej. Redis): **clave canónica**, TTL, invalidación en escrituras.
- Coherencia eventual aceptada y ventanas de staleness.

### Límites y timeouts

- Parámetros de sesión: `statement_timeout`, `lock_timeout`, `idle_in_transaction_session_timeout`.
- Pool de conexiones (tamaño, `max_overflow`, `pool_pre_ping`).
- Límites por rol/servicio para evitar **thundering herd**.

### Presupuesto de costos

- Guardrails de costo (consultas máximas/scan bytes por job, cuotas por entorno).
- Señales para **regresión de costos** y responsables de aprobación.

### Pruebas de performance

- Metodología: `EXPLAIN (ANALYZE, BUFFERS)`/plan cache, datasets sintéticos y de staging.
- **Baseline** antes/después, criterios de éxito (p95/p99 mejora ≥ X%).
- Repetibilidad: scripts y semillas de datos versionados.

### Observabilidad de base de datos

- Umbral de **slow queries** (p. ej., > 300 ms) y ruta de logs.
- Métricas: bloat/fragmentación, autovacuum, locks, hit ratio, uso de índices.
- Dashboards y alertas (enlace) y **runbooks** de remediación.
- **Integración con herramientas de observabilidad**: incluir enlaces a la configuración de alertas
  y a dashboards en herramientas como Datadog, Grafana o equivalentes, para que desarrolladores y
  copilotos puedan monitorear rendimiento en tiempo real y tomar decisiones informadas.

### Despliegue seguro de cambios de performance

- Índices en producción: creación **concurrente** (si aplica), backfill y validación.
- Feature flags/rollout gradual para cambios en consultas.
- Plan de **rollback** y criterios de abortar el cambio.

### Compatibilidad y extensiones

- Versiones del motor soportadas y **extensiones** habilitadas (con justificación).
- Impacto en portabilidad entre entornos.

### Anexos (opcional)

- Ejemplos `EXPLAIN` de consultas críticas (antes/después).
- Tabla “consulta ↔ índice” que mapea qué índice beneficia a cada patrón.

---

## Formato y consistencia del documento

Este documento debe cumplir las pautas de [`markdown-guidelines.md`](markdown-guidelines.md),
incluyendo:

- Encabezados **ATX** (`#`, `##`, `###`), no subrayados.
- Un único encabezado H1 al inicio del documento.
- Línea en blanco antes y después de cada encabezado.
- Tablas con primera fila de encabezado y formato estándar de Markdown (sin alineación manual).
- Bloques de código con fences y lenguaje especificado.
- Nombres de archivo y estructura conforme a las convenciones oficiales.

### Cumplimiento automatizado y validación

Para asegurar la coherencia del modelo de datos y el código, se requiere el uso de herramientas de
validación automatizada en el ciclo de desarrollo. Un _linter_ o _hook_ de pre-commit debe validar
las siguientes reglas:

- **Convenciones de nombres**: todas las entidades (tablas), colecciones y campos deben adherirse a
  la convención `snake_case`. Los nombres de las claves foráneas deben seguir el formato
  `<entidad>_id`.
- **Campos estándar**: verificar la existencia de los campos `created_at` y `updated_at` en todas
  las tablas que lo requieran.
- **Documentación de PII**: la presencia de la tabla de inventario de PII es obligatoria en cada
  documento `database.md`. El linter debe validar que los campos clasificados como PII en el código
  se correspondan con la documentación.
- **Relaciones**: los scripts de migración que crean claves foráneas deben tener una relación
  explícita documentada en [`database-er.md`](database-er.md).

La implementación de estas validaciones será responsabilidad del equipo de **DevOps** o **SRE** del
proyecto.

**Nota AI-Driven SDLC:** La integración del copiloto de IA con estas herramientas permite que valide
automáticamente el código que sugiere y corrija proactivamente cualquier desviación, garantizando
cumplimiento de estándares desde el primer momento.
