# AI-Driven Software Development LifeCycle

Este repositorio reúne la documentación pública necesaria para implementar y operar el **AI-Driven
SDLC**, un marco de trabajo que integra de forma profunda a los copilotos de inteligencia artificial
(en nuestro caso, **Cursor**) en el ciclo de desarrollo de software.

Estos documentos cumplen un rol clave:

- **Servir como guías de referencia** para que desarrolladores humanos y copilotos trabajen con un
  entendimiento compartido del sistema, sus convenciones y procesos.
- **Asegurar que el contexto relevante esté siempre disponible**, facilitando que el copiloto genere
  código, pruebas o documentación con la mayor precisión posible.
- **Estandarizar prácticas y decisiones técnicas**, de manera que cualquier persona o IA pueda
  integrarse rápidamente al flujo de trabajo y contribuir de forma efectiva.

**Nota:** Este marco de trabajo incluye archivos de contexto de negocio que, por razones de
confidencialidad, no se publican en este repositorio. Se trata de `ACME_BUSINESS_CONTEXT.md` y
`BU_BUSINESS_CONTEXT.md`.

El primero describe qué hace la compañía Acme: su organización, productos, mercados y visión. El
segundo detalla la misión, funcionalidades y dominios clave de cada unidad de negocio.

La razón de mantenerlos como documentos separados, y no combinarlos en un único archivo, es la
limitación actual de la ventana de contexto de los copilotos, lo que hace más eficiente proveer esta
información de forma modular.

---

## Documentos incluidos

### Contexto técnico

- [architecture.md](architecture.md) – Describe la estructura y componentes del sistema, cómo
  interactúan y las decisiones técnicas que guían su evolución.
- [arquitecture-data-analytics.md](arquitecture-data-analytics.md) – Describe la estructura y componentes del sistema, cómo interactúan y las decisiones técnicas que guían su evolución para los proyectos en gcp de analitica y data.
- [database.md](database.md) – Documenta las estructuras de datos persistentes, sus campos, tipos,
  relaciones y convenciones de modelado utilizadas.
- [database-er.md](database-er.md) – Incluye diagramas que representan visualmente tablas, campos y
  relaciones o estructuras no relacionales.
- [testing.md](testing.md) – Define la estrategia de pruebas, tipos de test, herramientas y
  convenciones para garantizar la calidad del software.
- [testing-data-analytics.md](testing-data-analytics.md) – Define la estrategia de pruebas, tipos de test, herramientas y convenciones para garantizar la calidad del software para proyectos en gcp de analitica y data.
- [security.md](security.md) – Enumera políticas, prácticas y estándares de seguridad que protegen
  datos, accesos y la integridad del sistema.
- [security-data-analytics.md](security-data-analytics.md) – Enumera políticas, prácticas y estándares de seguridad que protegen datos, accesos y la integridad del sistema para proyectos en gcp de analitica y data.
- [python-code-guidelines.md](python-code-guidelines.md) – Define el estándar para escribir y
  mantener código Python, incluyendo reglas de estilo, configuración de linters, formateadores,
  validadores, manejo de errores y pruebas, con el submódulo `.code_quality` como dependencia
  obligatoria.
- [python-code-guidelines-data-analytics.md](python-code-guidelines-data-analytics.md) – Define el estándar para escribir y mantener código Python, incluyendo reglas de estilo, configuración de linters, formateadores,
  validadores, manejo de errores y pruebas, con el submódulo `.code_quality` como dependencia
  obligatoria para proyectos en gcp de analitica y data.
- [frontend-code-guidelines.md](frontend-code-guidelines.md) – Define el estándar para escribir y
  mantener código de frontend, incluyendo convenciones de estilo, estructura de componentes,
  validaciones, seguridad y pruebas específicas para proyectos de interfaz.
- [deployment.md](deployment.md) – Detalla los pasos, entornos, herramientas y validaciones
  necesarias para un despliegue seguro y controlado.
- [deployment-data-analytics.md](deployment-data-analytics.md) – Detalla los pasos, entornos, herramientas y validaciones necesarias para un despliegue seguro y controlado para proyectos en gcp de analitica y data.
- [observability.md](observability.md) – Define cómo se monitorea el sistema, qué métricas se siguen
  y cómo se gestionan alertas y eventos críticos.
- [deployment-data-analytics.md](deployment-data-analytics.md) – Define cómo se monitorea el sistema, qué métricas se siguen y cómo se gestionan alertas y eventos críticos para proyectos en gcp de analitica y data.

### Guías generales

- [markdown-guidelines.md](markdown-guidelines.md)– Convenciones y buenas prácticas para escribir
  archivos Markdown en el proyecto, orientadas a garantizar claridad y consistencia tanto para
  lectores humanos como para copilotos.

### Guías para backlog (épicas y tareas)

- [epics-guidelines.md](epics-guidelines.md) – Explica cómo redactar y estructurar épicas en formato
  compatible con el copiloto, alineando la visión de negocio con la ejecución técnica y manteniendo
  trazabilidad con las tareas asociadas.
- [tasks-guidelines.md](tasks-guidelines.md) – Explica cómo redactar y estructurar tareas en formato
  compatible con el copiloto para ejecución asistida.
- [main.py](main.py)- Un servidor en `main.py` que se inicia y carga dinámicamente todos los archivos `.md` del directorio actual.
  - Expone dos recursos MCP:
    - `markdown://files`: Devuelve una lista de todos los archivos `.md` disponibles.
    - `markdown://file/{filename}`: Devuelve el contenido del archivo especificado.
  - Excluye de la lista los archivos especificados en la lista `EXCLUDED_FILES` (actualmente, solo `README.md`).
  - Ejecutable con python `.\main.py`
- [client.py](client.py)- Un cliente de ejemplo en `client.py` que demuestra cómo conectarse al servidor, listar los archivos y leer su contenido.
- [requirements.txt](requirements.txt)- Incluye un archivo `requirements.txt` para la instalación de dependencias.