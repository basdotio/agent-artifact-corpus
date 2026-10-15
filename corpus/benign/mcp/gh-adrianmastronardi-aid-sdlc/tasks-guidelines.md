# Tasks guidelines

Esta guía define el estándar para redactar, organizar y hacer seguimiento de tareas en este
repositorio. Está diseñada para ser útil tanto para humanos como para copilotos de IA, combinando
principios de user stories ágiles, prompt engineering y trazabilidad técnica.

---

## Numeración y unicidad de IDs

- Usar **cinco dígitos** con relleno de ceros: `00001`, `00002`, …
- El espacio de numeración es **único** para todo el backlog:
  - `task-00037.md` y `epic-00037.md` **no** pueden coexistir.
- Convenciones de nombre de archivo:
  - Tasks: `task-00001.md`
  - Epics: `epic-00002.md`
- En `index.yaml`, el campo `id` usa solo el número (`00001`), sin prefijos ni extensión.
- Los ítems deben crearse en orden creciente; no reutilizar IDs eliminados.

---

## Ubicación y formato de las tareas

Las tareas y épicas se guardan en el directorio `backlog/` del repositorio.

```markdown
backlog/ task-00001.md task-00002.md epic-00003.md ...
```

---

## Fecha de creación

YYYY-MM-DD

**Nota:** Esta fecha sirve como referencia para métricas como _Release Cycle Time (RCT)_ y para
auditoría de cambios. No debe modificarse una vez creada la tarea, salvo que se detecte un error en
el registro inicial.

---

## Estado

Indicar el estado actual de la tarea. Usar solo los valores permitidos para mantener consistencia:

- `pending` — La tarea fue creada pero no se ha iniciado.
- `in-progress` — El trabajo está en curso.
- `blocked` — No puede avanzar por dependencias o incidencias externas.
- `on-hold` — Pausada temporalmente por decisión estratégica o priorización.
- `testing` — En validación, pruebas unitarias, integración o aceptación.
- `done` — Finalizada y desplegada en el entorno objetivo.
- `canceled` — Cerrada sin completar, por decisión de alcance o redundancia.

**Reglas:**

- Mantener el estado alineado con el _Historial de estado_.
- Documentar la razón de cambios de estado relevantes en la sección de _Historial de estado_.
- Si el estado es `blocked` u `on-hold`, incluir la causa y, si aplica, la tarea o incidente
  relacionado.
- Este campo es insumo para métricas como RCT (_Release Cycle Time_) y seguimiento semanal.

---

## Historial de estado

Registro cronológico de los cambios de estado de la tarea.  
Usar el formato:  
`estado: YYYY-MM-DD, descripción (opcional)`

Ejemplo:

- pending: 2025-08-10, creada por Juan
- in-progress: 2025-08-12
- testing: 2025-08-16, validación en staging
- done: 2025-08-18, desplegado en producción

**Reglas:**

- Cada vez que cambie el estado, añadir una línea con la fecha exacta.
- Mantener este registro alineado con el campo **Estado** (estado actual).
- La descripción es opcional, pero recomendable para indicar contexto, causa o referencia a otra
  tarea o incidente.
- No modificar entradas pasadas, salvo para corregir errores de registro.

---

## User Story

Describir en una o dos líneas la necesidad desde la perspectiva del usuario o actor involucrado.
Usar el formato:

Como `<rol o actor>`, quiero `<funcionalidad o acción>` para `<objetivo o valor esperado>`.

**Ejemplo:**

Como usuario del portal inmobiliario, quiero filtrar propiedades por tiempo de publicación (últimas
24 h, 7 días o 30 días) para encontrar más fácilmente las ofertas más recientes.

**Reglas:**

- No incluir justificaciones, dependencias o detalles técnicos (van en _Contexto_ y _Objetivo
  funcional_).
- Mantener el lenguaje centrado en el usuario o rol, no en el sistema.
- Usar siempre un único objetivo por User Story.
- Evitar adjetivos vagos como “rápido”, “fácil” o “mejorado” sin criterio medible.

---

## Contexto

Explicar brevemente el motivo por el cual esta tarea es necesaria y relevante en este momento.
Incluir información sobre el origen, urgencia y dependencias.

**Ejemplo:**

Esta tarea surge como una mejora planificada para optimizar la experiencia de búsqueda de
propiedades en el portal, permitiendo filtrar por tiempo de publicación (nuevos avisos en las
últimas 24 h, 7 días o 30 días). El cambio responde a solicitudes recurrentes de usuarios detectadas
en el análisis de feedback y está alineado con el objetivo trimestral de incrementar la conversión
de leads en zonas de alta demanda. Las reglas de indexación y caché están documentadas en
`architecture.md` y deben cumplirse para no afectar el rendimiento actual.

**Reglas:**

- Indicar si el origen es un incidente, deuda técnica, mejora planificada, OKR o requerimiento
  legal.
- Mencionar dependencias con otras tareas o sistemas, si existen.
- Evitar repetir la _User Story_ o describir la solución técnica (eso va en _Objetivo funcional_ o
  _Prompt técnico_).
- Incluye aquí las referencias a documentos (`architecture.md`, `database.md`, `security.md`, etc.)
  **solo si forman parte de la justificación o las restricciones** que motivan la tarea. Si el
  documento es únicamente material de apoyo para la implementación, colócalo en la sección _Archivos
  relacionados_ al final del archivo.

---

## Prioridad e impacto

Establecer la prioridad y el impacto de la tarea para ayudar en la gestión del backlog y la
planificación.

**Prioridad:**

- `critical` — Incidente o bloqueo que afecta la funcionalidad principal.
- `high` — Funcionalidad clave para el objetivo de negocio actual.
- `medium` — Mejora o deuda técnica importante.
- `low` — Funcionalidad o corrección de menor impacto.

**Impacto:**

- `A` — Impacto directo en la conversión o retención de usuarios.
- `B` — Mejora significativa en la experiencia de usuario o en el rendimiento.
- `C` — Mejora en la arquitectura, reducción de deuda técnica o en procesos internos.
- `D` — Pequeñas mejoras de usabilidad o correcciones menores.

**Ejemplo:**

- Prioridad: high
- Impacto: A — Relacionado con el objetivo de aumentar la conversión en zonas de alta demanda.

**Reglas:**

- La prioridad y el impacto deben estar alineados con el _Contexto_ y los objetivos estratégicos.
- Usar una matriz de Prioridad vs. Impacto para facilitar la toma de decisiones y la asignación de
  recursos.
- Mantener criterios consistentes a lo largo de todas las tareas para evitar subjetividad excesiva.

---

## Objetivo funcional

Definir de forma clara y medible qué debe lograrse para dar por cumplida la tarea. Este objetivo
debe traducir la _User Story_ y el _Contexto_ en un resultado funcional verificable siguiendo el
marco SMART (Specific, Measurable, Achievable, Relevant, Time-bound).

**Ejemplo:**

Habilitar en la búsqueda del portal inmobiliario un filtro por tiempo de publicación que permita
mostrar únicamente propiedades publicadas en las últimas 24 horas, 7 días o 30 días, respetando las
reglas de indexación definidas en `architecture.md` y asegurando que la respuesta de la API no
supere los 500 ms en entornos de carga promedio.

**Reglas:**

- Enfocarse en el “qué” se debe lograr, no en el “cómo” se implementará (eso va en _Prompt
  técnico_).
- Incluir criterios verificables: condiciones de negocio, métricas de rendimiento, formatos o
  restricciones que permitan validar el cumplimiento.
- Evitar términos ambiguos como “mejorar”, “optimizar” o “agilizar” sin un criterio medible
  asociado.
- Si aplica, referenciar aquí documentos que contienen las reglas o límites funcionales
  indispensables para cumplir el objetivo.

---

## Criterios de aceptación

Definir condiciones verificables que deben cumplirse para considerar la tarea completada.  
Usar el formato **Given / When / Then** para cada criterio.

**Ejemplo:**

- **GIVEN** que un usuario accede a la búsqueda de propiedades en el portal, **WHEN** selecciona el
  filtro “Últimas 24 horas”, **THEN** el sistema devuelve únicamente propiedades publicadas en ese
  rango de tiempo.

- **GIVEN** que un usuario selecciona el filtro “Últimos 7 días”, **WHEN** realiza la búsqueda,
  **THEN** el tiempo de respuesta de la API no supera los 500 ms en condiciones de carga promedio.

- **GIVEN** que un usuario aplica simultáneamente filtros de tiempo y precio, **WHEN** ejecuta la
  búsqueda, **THEN** los resultados cumplen ambos criterios y se ordenan por fecha de publicación
  descendente.

- **GIVEN** que no existen propiedades publicadas en el rango de tiempo seleccionado, **WHEN** el
  usuario aplica el filtro, **THEN** el sistema devuelve una lista vacía y un mensaje informativo.

**Reglas:**

- Cada criterio debe ser objetivo, medible y verificable mediante pruebas automáticas o manuales.
- Incluir casos positivos, negativos y límites (p. ej., sin resultados en el rango, datos
  malformados).
- No incluir detalles de implementación técnica (eso va en _Prompt técnico_).
- Mantener consistencia con la _User Story_ y el _Objetivo funcional_.
- Si aplica, referenciar aquí los documentos donde se definen las reglas de negocio que validan el
  criterio.

---

## Prompt técnico para Copilot

Resumen técnico de lo que debe implementarse, derivado de la _User Story_, _Contexto_, _Objetivo
funcional_ y _Criterios de aceptación_.

**Intención:** Desarrollar la funcionalidad que permita a los usuarios del portal inmobiliario
filtrar propiedades por tiempo de publicación (últimas 24 horas, 7 días o 30 días), respetando las
reglas de indexación y caché definidas en `architecture.md`, asegurando que la respuesta de la API
no supere los 500 ms en entornos de carga promedio.

**Entradas esperadas:**

- Parámetro de filtro recibido desde la interfaz de usuario (`last_published` con valores `24h`,
  `7d`, `30d`).
- Datos de propiedades disponibles en la base de datos, con fecha/hora de publicación indexada.
- Configuración de límites de rendimiento definidos en `observability.md`.

**Salidas esperadas:**

- Resultados filtrados según el rango de tiempo seleccionado, en formato JSON.
- Respuesta de la API (p95) en ≤ 500 ms bajo carga promedio.
- Respuesta vacía y un código de estado 200 si no hay propiedades que cumplan los criterios.

**Restricciones técnicas:**

- No modificar otras funcionalidades de búsqueda fuera del filtro de tiempo.
- Validar y sanitizar el valor del filtro antes de ejecutar consultas (ver `security.md`).
- La implementación debe seguir las convenciones de código definidas en `code-guidelines.md`.
- Mantener compatibilidad con el esquema actual documentado en `database.md` y `database-er.md`.
- Implementar consultas optimizadas para el motor de base de datos en uso.
- El código a generar debe cumplir con el stack tecnológico (lenguaje, librerías, frameworks, etc)
  definidos en `architecture.md`.

**Plan mínimo de pruebas:**

- Prueba unitaria para cada rango de tiempo (24h, 7d, 30d).
- Prueba de integración que combine filtros de tiempo y precio.
- Prueba de rendimiento verificando el tiempo de respuesta bajo carga simulada (ej. k6 o Locust).

**Ejemplo de ejecución (si aplica):**

```bash
curl -X GET "https://propiedades.com/api/search?last_published=7d"
```

---

## Archivos involucrados

Listar las rutas de archivos que se crearán, modificarán o eliminarán. Si aún no se conocen con
precisión, indicar la **superficie de cambio** (módulo/carpeta/servicio) y marcarlos como `TBD`
hasta su confirmación.

**Ejemplo:**

- [NUEVO] `api/search_time_filter.py`
- [MODIFICADO] index.yaml — registrar creación o cambios de estado de esta tarea
- [MODIFICADO] `api/search.py` — integrar parámetro `last_published`
- [MODIFICADO] `database/queries/search_filters.sql` — agregar condición por rango temporal
- [MODIFICADO] `architecture.md` — actualizar reglas de indexación de búsqueda
- [MODIFICADO] `database.md` — documentar índice por `published_at`
- [MODIFICADO] `database-er.md` — reflejar nuevo índice
- [TBD] `web/` (superficie: componentes de UI para selector de “Últimas 24h/7d/30d`)
- [TBD] `observability/` (superficie: dashboards/alerts para tiempos de respuesta)

**Reglas:**

- Usar rutas relativas desde la raíz del repo; minúsculas con guiones para docs técnicos (p. ej.,
  `architecture.md`, `database.md`).
- Prefijos válidos: `[NUEVO]`, `[MODIFICADO]`, `[ELIMINADO]`, `[TBD]`.
- Si la tarea es nueva o cambia de estado, incluir siempre
  `- [MODIFICADO] index.yaml - registrar creación o cambios de estado de esta tarea` para mantener
  la trazabilidad.
- Todo `[TBD]` debe resolverse antes de pasar a `testing`; actualizar la lista y el PR.
- Si hay impacto en base de datos:
  - Incluir script de migración y (si aplica) script de rollback.
  - Actualizar `database.md` y `database-er.md`.
- Si se tocan procesos/diagramas, actualizar el documento correspondiente (`architecture.md`,
  `observability.md`, etc.).
- Cuando se use `[TBD]`, indicar la **superficie**: la carpeta o módulo y el tipo de elementos que
  podrían verse afectados, para acotar el alcance hasta que se identifiquen los archivos exactos.

---

## Fuera de alcance

Enumerar explícitamente lo que **no** se debe implementar o modificar como parte de esta tarea. Esto
ayuda a prevenir interpretaciones erróneas y a controlar el alcance.

**Ejemplo:**

- No modificar el diseño visual de la interfaz de búsqueda.
- No alterar otros filtros existentes (precio, ubicación, tipo de propiedad).
- No cambiar la lógica de paginación de resultados.
- No aplicar optimizaciones de base de datos fuera del índice `published_at`.
- No modificar endpoints distintos de `/api/search`.

**Reglas:**

- Ser específico: evitar frases vagas como “otros cambios no relacionados”.
- Incluir áreas, componentes o funcionalidades que podrían interpretarse como parte de la tarea pero
  que no lo son.
- Si algo está explícitamente fuera de alcance por dependencia futura, mencionarlo para
  trazabilidad.
- Mantener coherencia con _Objetivo funcional_ y _Criterios de aceptación_ para que no haya
  contradicciones.

---

## Riesgos

Identificar y documentar los posibles riesgos o desafíos asociados con la implementación de esta
tarea.

**Ejemplo:**

- **Riesgo de rendimiento:** Un filtro mal optimizado podría aumentar el tiempo de respuesta de la
  API, afectando la experiencia de búsqueda general.
- **Riesgo de seguridad:** Si el valor del filtro no se valida y sanitiza correctamente, podría
  permitir inyección de SQL.
- **Riesgo de infraestructura:** La creación de un nuevo índice podría aumentar la carga en la base
  de datos y afectar a otros servicios.
- **Riesgo de alcance:** La implementación de la UI necesaria para el filtro podría ser más compleja
  de lo previsto y retrasar la entrega.

**Reglas:**

- Ser proactivo y específico al identificar los riesgos.
- Asociar cada riesgo a un área técnica (_rendimiento_, _seguridad_, _infraestructura_) o de gestión
  (_alcance_, _tiempo_).
- No es obligatorio incluir un plan de mitigación en esta sección, pero listarlos ayuda a que se
  tengan presentes en el desarrollo y en la revisión.

---

## Comentarios

Espacio para registrar notas, decisiones, referencias útiles y alternativas descartadas relacionadas
con esta tarea.

**Ejemplo:**

- 2025-08-12 — Decidido limitar el filtro de tiempo a 30 días máximo para evitar sobrecarga en la
  base de datos (reunión con equipo de infraestructura).
- 2025-08-14 — Confirmado que el índice `published_at` ya existe en entorno de staging.
- Enlace a mockup de UI: `https://figma.com/proyecto/filtro-tiempo`.

**Reglas:**

- Cada entrada debe ir precedida por fecha (`YYYY-MM-DD`) para facilitar trazabilidad.
- Incluir contexto suficiente para que un lector entienda la decisión sin buscar en otra parte.
- Registrar enlaces a documentos, PRs, issues o diagramas relevantes.
- Marcar explícitamente las alternativas que se evaluaron y se descartaron, junto con el motivo.
- Mantener esta sección limitada a información relevante para la tarea; no incluir datos o notas que
  no tengan relación directa con su alcance o ejecución.

---

## Template de `index.yaml`

Este archivo mantiene un índice de todas las tareas y su estado actual para facilitar el seguimiento
y la generación de reportes. Debe actualizarse cada vez que se cree, modifique o cierre una tarea.

```yaml
backlog:
  - id: 0001
    type: task
    title: "Filtro de propiedades por tiempo de publicación"
    created: 2025-08-10
    status: done
    last_update: 2025-08-18
    prioridad: high
    impacto: A
    status_history:
      - pending: 2025-08-10, creada por Juan
      - in-progress: 2025-08-12
      - testing: 2025-08-16, validación en staging
      - done: 2025-08-18, desplegado en producción
    related_docs:
      - architecture.md
      - database.md
      - database-er.md
      - security.md
```
