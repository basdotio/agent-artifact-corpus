# Epics guidelines

Esta guía define el estándar para redactar, organizar y hacer seguimiento de épicas en este
repositorio. Está diseñada para alinear la visión de negocio con la ejecución técnica, facilitando
el trabajo conjunto entre humanos y copilotos de IA.

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

## Ubicación y formato de las épicas

Las tareas y épicas se guardan en el directorio `backlog/` del repositorio.

```markdown
backlog/ task-00001.md task-00002.md epic-00003.md ...
```

---

## Fecha de creación

YYYY-MM-DD

**Nota:** Esta fecha sirve como referencia para planificación y para métricas como _Epic Cycle Time_
o _Lead Time_. No debe modificarse una vez creada la épica.

---

## Estado

Usar solo los valores permitidos para mantener consistencia:

- `pending` — La épica fue creada pero no se ha iniciado.
- `in-progress` — Alguna de las historias asociadas está en desarrollo.
- `blocked` — No puede avanzar por dependencias o incidencias externas.
- `on-hold` — Pausada temporalmente por decisión estratégica o priorización.
- `done` — Todas las historias asociadas están finalizadas.
- `canceled` — Cerrada sin completar, por decisión de alcance o redundancia.

**Reglas:**

- Mantener el estado alineado con el _Historial de estado_.
- Documentar la razón de cambios de estado relevantes en la sección de _Historial de estado_.
- Si el estado es `blocked` u `on-hold`, incluir la causa y, si aplica, la tarea o incidente
  relacionado.
- Este campo es insumo para métricas como RCT (_Release Cycle Time_) y seguimiento semanal.

---

## Historial de estado

Registro cronológico de cambios de estado de la épica.  
Formato:  
`estado: YYYY-MM-DD, descripción (opcional)`

Ejemplo:

- pending: 2025-08-10, creada por Juan
- in-progress: 2025-08-12
- done: 2025-08-18, desplegado en producción

**Reglas:**

- Cada vez que cambie el estado, añadir una línea con la fecha exacta.
- Mantener este registro alineado con el campo **Estado** (estado actual).
- La descripción es opcional, pero recomendable para indicar contexto, causa o referencia a otra
  épica, tarea o incidente.
- No modificar entradas pasadas, salvo para corregir errores de registro.

---

## Descripción general

Explicar en un párrafo el propósito central de la épica, el valor que aporta al negocio y su
relación con los objetivos estratégicos de la organización. Debe permitir que cualquier miembro del
equipo entienda el “para qué” de la épica sin necesidad de revisar las tareas asociadas.

**Ejemplo:**

Esta épica tiene como objetivo implementar un nuevo motor de búsqueda en el portal inmobiliario que
permita consultas más rápidas y precisas, integrando filtros avanzados de geolocalización y tiempo
de publicación. Su implementación busca mejorar la experiencia del usuario, aumentar la conversión
de leads y sostener la competitividad frente a otros portales líderes del mercado.

**Reglas:**

- Mantener el lenguaje claro y orientado a negocio, evitando detalles de implementación técnica (eso
  va en _Historias / tareas asociadas_ o _Prompt técnico_ de las tasks).
- Incluir, si aplica, referencias a OKRs, KPIs u objetivos trimestrales.
- Evitar repetir la _User Story_ o los objetivos ya documentados en tareas específicas.
- Si la épica surge de un incidente, deuda técnica o requerimiento legal, indicarlo brevemente.

---

## Objetivos clave

Enumerar de forma clara y medible los resultados que se espera alcanzar con la épica. Cada objetivo
debe estar alineado con OKRs o KPIs y permitir evaluar el éxito de la implementación.

**Ejemplo:**

- Reducir el tiempo promedio de respuesta de búsqueda de 900 ms a ≤ 500 ms (p95) en el portal
  inmobiliario.
- Incrementar en un 15 % la conversión de leads en zonas de alta demanda dentro de los tres meses
  posteriores al lanzamiento.
- Implementar filtros avanzados de búsqueda por geolocalización y tiempo de publicación.
- Garantizar compatibilidad con la arquitectura actual y sin degradar el rendimiento de otras
  funciones críticas.

**Reglas:**

- Redactar objetivos siguiendo el marco **SMART** (_Specific, Measurable, Achievable, Relevant,
  Time-bound_).
- Mantener entre 3 y 5 objetivos clave para asegurar foco y viabilidad.
- Si un objetivo está condicionado a un entregable de otra área o equipo, indicarlo claramente.
- Usar métricas cuantitativas siempre que sea posible para facilitar la evaluación posterior.

---

## Tareas asociadas

Lista de tareas (`task-XXXXX.md`) que forman parte de esta épica, referenciadas con su ruta relativa
completa para facilitar la trazabilidad y navegación.

**Ejemplo:**

- backlog/task-00012.md
- backlog/task-00015.md
- backlog/task-00016.md

**Reglas:**

- Usar siempre la ruta relativa completa desde la raíz del repositorio.
- Mantener la lista actualizada conforme se añadan o eliminen tareas.
- Si una tarea es eliminada o reemplazada, registrar el cambio en _Comentarios_.
- En `associated_tasks` de `index.yaml`, usar siempre la ruta relativa desde la raíz del repositorio
  (por ejemplo: backlog/task-00012.md).

---

## Prioridad e impacto

Usar la misma clasificación que en `tasks-guidelines.md` para mantener consistencia.

---

## Definición de métricas

Establecer de forma clara y medible los indicadores que se usarán para evaluar el éxito de la
épica.  
Estas métricas deben definirse al inicio y mantenerse estables durante toda la ejecución para
garantizar trazabilidad.

**Ejemplo:**

- **% de tareas completadas:** proporción de tasks asociadas en estado `done` sobre el total.
- **Métrica de negocio:** incremento del porcentaje de conversión de leads en zonas de alta demanda.
- **Métrica técnica:** tiempo de respuesta promedio (p95) en búsquedas ≤ 500 ms.
- **Métrica de experiencia de usuario:** satisfacción ≥ 4.5/5 en encuestas NPS posteriores al
  lanzamiento.

**Reglas:**

- Incluir al menos una métrica de ejecución, una de negocio y, si aplica, una técnica o de
  experiencia de usuario.
- Las métricas deben cumplir el marco SMART (Specific, Measurable, Achievable, Relevant,
  Time-bound).
- Mantener coherencia con los _Objetivos clave_ y, si corresponde, con OKRs o KPIs de la
  organización.
- Evitar métricas vagas o sin unidad de medida clara.

---

## Registro de avance y logros

Documentar el progreso real de la épica a lo largo del tiempo, registrando logros parciales, hitos
alcanzados y cambios en los valores de las métricas definidas. No es necesario que la épica esté en
`done` para que se registren avances.

**Ejemplo:**

- **2025-09-10** — % de tareas completadas: 40 % (4 de 10). Tiempo de respuesta promedio bajó de 900
  ms a 720 ms (p95).
- **2025-09-20** — % de tareas completadas: 70 %. Conversión en zonas de alta demanda incrementada
  en un 8 %.
- **2025-10-05** — % de tareas completadas: 90 %. NPS post-lanzamiento parcial: 4.6/5.

**Reglas:**

- Incluir siempre la fecha de cada registro.
- Reflejar cambios relevantes en los valores de las métricas definidas.
- Usar _Comentarios_ para documentar contexto o justificación de cambios significativos.
- Mantener el registro ordenado cronológicamente y alineado con el _Historial de estado_.

---

## Riesgos

Identificar y documentar los posibles riesgos o desafíos asociados con la ejecución de esta épica.
Deben considerarse tanto riesgos técnicos como de negocio o gestión, y revisarse periódicamente
durante el ciclo de vida de la épica.

**Ejemplo:**

- **Riesgo de rendimiento:** Integraciones múltiples podrían degradar el tiempo de respuesta en
  consultas críticas.
- **Riesgo de seguridad:** Exposición de datos sensibles si no se cumplen las políticas de
  `security.md` durante la implementación.
- **Riesgo de alcance:** Las tareas necesarias para completar la épica podrían requerir mayor
  esfuerzo del estimado inicial.
- **Riesgo de dependencias externas:** Retrasos en la disponibilidad de APIs de terceros pueden
  bloquear avances clave.

**Reglas:**

- Ser proactivo y específico al identificar riesgos.
- Asociar cada riesgo a un área técnica (_rendimiento_, _seguridad_, _infraestructura_) o de gestión
  (_alcance_, _tiempo_, _dependencias_).
- Actualizar la sección si surgen nuevos riesgos o cambian los existentes.
- No es obligatorio incluir un plan de mitigación, pero se recomienda registrar notas en
  _Comentarios_ si existen acciones preventivas.

---

## Comentarios

Espacio para registrar notas, decisiones estratégicas, referencias útiles y alternativas evaluadas o
descartadas que impacten el desarrollo de la épica.  
Esta sección debe servir como registro vivo de la conversación y el razonamiento detrás de
decisiones clave.

**Ejemplo:**

- **2025-09-15** — Se decidió priorizar el desarrollo de la API de filtrado antes que la UI, para
  habilitar pruebas tempranas de rendimiento.
- **2025-09-22** — Reunión con equipo de marketing: confirmada la relevancia de esta épica para el
  objetivo de conversión del trimestre.
- **2025-09-28** — Evaluada y descartada la integración con proveedor externo X por sobrecostos de
  licenciamiento.

**Reglas:**

- Cada entrada debe iniciar con fecha en formato `YYYY-MM-DD`.
- Incluir contexto suficiente para entender la decisión sin buscar en otra parte.
- Referenciar tareas (`task-XXXXX.md`), documentos (`architecture.md`, `security.md`, etc.) o
  enlaces relevantes.
- Mantener esta sección alineada con el _Registro de avance y logros_ para que refleje decisiones
  que hayan afectado el progreso.

## Template de `index.yaml` para épicas

Este archivo mantiene un índice de todas las épicas y su estado actual para facilitar el seguimiento
y la generación de reportes.  
Debe actualizarse cada vez que se cree, modifique o cierre una épica.

```yaml
epics:
  - id: 00003
    title: "Nuevo motor de búsqueda con filtros avanzados"
    created: 2025-08-10
    status: in-progress
    last_update: 2025-09-20
    prioridad: high
    impacto: A
    status_history:
      - pending: 2025-08-10, creada por Juan
      - in-progress: 2025-08-15, inicio de desarrollo
    associated_tasks:
      - backlog/task-00012.md
      - backlog/task-00015.md
      - backlog/task-00016.md
```
