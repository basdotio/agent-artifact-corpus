# Filosofía de Arquitectura para Desarrollo Asistido por IA

## Propósito

Este documento establece los principios filosóficos y las buenas prácticas que gobiernan la arquitectura de software en un entorno de desarrollo asistido por IA. Define cómo diseñar sistemas que no solo sean mantenibles por humanos, sino que también maximicen la efectividad de los agentes de IA como copilotos de desarrollo.

---

## Principios Fundamentales

### 1. Contexto Vivo como Artefacto de Primera Clase

En un entorno asistido por IA, **el código y su contexto deben evolucionar juntos**. El contexto no es documentación opcional que envejece: es un artefacto de primera clase que asegura que las decisiones, su propósito y sus consecuencias se mantengan accesibles y actualizadas.

**Principios clave:**
- **Code should tell a story, not just compile**: El flujo desde la entrada de datos hasta el resultado final debe ser legible y coherente.
- **Docs live beside the code, searchable and semantic**: La documentación relevante vive junto al código, enlazada y fácil de buscar.
- **APIs are boringly predictable**: Rutas, métodos y formatos de respuesta siguen patrones consistentes.
- **Constraints are just tight enough to prevent chaos**: Reglas claras limitan la dispersión sin ahogar la flexibilidad.

### 2. Reducción de Fricción Cognitiva

El diseño arquitectónico debe minimizar la carga cognitiva tanto para humanos como para agentes de IA:

- **Vertical slices sobre layering**: Agrupar todo lo necesario para una funcionalidad en un mismo módulo.
- **Frameworks opinados**: Preferir tecnologías que impongan estructura coherente y predecible.
- **Convenciones explícitas**: Definir patrones claros que reduzcan la necesidad de "adivinar" intenciones.

### 3. Compatibilidad con IA como Criterio de Diseño

La compatibilidad con agentes de IA es ahora tan relevante como cualquier otro criterio de seguridad, rendimiento o mantenibilidad:

- **Estructuras que sirven como "contexto vivo"**: Frameworks que ofrecen arquitectura opinada y coherente.
- **Metadatos estructurados**: Tags, enlaces y referencias que faciliten la navegación semántica.
- **Diseño para contar una historia**: Slices claros y con propósito que actúen como capítulos completos.
- **Desarrollo local completo**: Todo el stack debe poder ejecutarse localmente para facilitar el lazo de feedback inmediato que permite a los agentes evaluar resultados mediante herramientas como curl, terminal o MCP e iterar rápidamente.

---

## Diagrama de Arquitectura de Software

### Modelado C4 como Lenguaje Ubicuo

El modelado C4 (Context, Containers, Components, Code) proporciona un lenguaje ubicuo que permite a humanos y agentes de IA comunicarse efectivamente sobre la arquitectura del sistema.

#### Nivel 1: Diagrama de Contexto (C4 Nivel 1)

**Propósito:** Mostrar el sistema de software dentro de su entorno, respondiendo a "¿Qué hace nuestro sistema y quiénes interactúan con él?"

**Elementos:**
- **Sistema de Interés**: Un solo bloque que representa todo el sistema de software.
- **Actores/Usuarios**: Personas que interactúan directamente con el sistema.
- **Sistemas Externos**: Otros sistemas de software con los que se comunica.

**Lineamientos:**
- Simplicidad es clave: No mostrar componentes internos o detalles de implementación.
- Enfoque en interacciones: Usar flechas para indicar flujo de información.
- Nomenclatura clara: Etiquetas que describan el propósito de la interacción.
- Lenguaje no técnico: Comprensible para desarrolladores y gerentes de negocio.

#### Nivel 2: Diagrama de Contenedores (C4 Nivel 2)

**Propósito:** Descomponer el sistema en sus contenedores principales, respondiendo a "¿Cómo se divide el sistema y qué tecnologías se usan?"

**Elementos:**
- **Sistema de Interés**: Representado como recuadro que contiene todos los contenedores.
- **Contenedores**: Bloques principales de la aplicación (aplicaciones, bases de datos, servicios).
- **Relaciones**: Flechas que muestran comunicación y flujo de datos entre contenedores.

**Lineamientos:**
- Identificar contenedores de despliegue: Cada aplicación o servicio principal.
- Etiquetar tecnología: Mencionar tecnología principal dentro de cada bloque.
- Describir interacciones: Indicar tipo de comunicación (API REST, SQL, etc.).
- Mantener perspectiva de alto nivel: No ir a detalles de clases o funciones.

### Definición de Dominios

Los dominios se definen basándose en:

1. **Cohesión funcional**: Funcionalidades que cambian por las mismas razones.
2. **Acoplamiento mínimo**: Interfaces claras y estables entre dominios.
3. **Contexto de negocio**: Alineación con conceptos del dominio de negocio.
4. **Compatibilidad con IA**: Dominios que pueden ser comprendidos y modificados de forma independiente.

---

## Stack Tecnológico

### Principios de Selección

1. **Frameworks Opinados**: Preferir tecnologías que impongan estructura coherente y predecible.
2. **Popularidad y Madurez**: Usar tecnologías establecidas con amplia documentación y comunidad.
3. **Compatibilidad con IA**: Frameworks que faciliten la comprensión y modificación por agentes de IA.
4. **Estándares**: Siempre que sea posible, usar estándares establecidos.

### Stack Recomendado

#### Frontend
- **React**: Framework opinado con ecosistema maduro y patrones establecidos.
- **TypeScript**: Tipado estático que mejora la comprensión del código por IA.
- **Next.js**: Framework full-stack que reduce la complejidad de configuración.

#### Backend
- **FastAPI**: Framework moderno con documentación automática y validación integrada.
- **SQLModel**: Combina SQLAlchemy y Pydantic, proporcionando modelos unificados.
- **Pydantic**: Validación y serialización que actúa como contrato vivo.

#### Base de Datos
- **PostgreSQL**: Base de datos relacional madura con excelente soporte para funciones avanzadas.
- **MySQL**: Base de datos relacional de código abierto, ampliamente adoptada y con excelente rendimiento para aplicaciones web.
- **MongoDB**: Base de datos NoSQL orientada a documentos, ideal para datos no estructurados o semiestructurados.
- **Elasticsearch**: Motor de búsqueda y análisis distribuido, excelente para búsquedas complejas y análisis de logs.
- **DynamoDB**: Base de datos NoSQL completamente administrada por AWS, con escalabilidad automática y latencia de un solo dígito.
- **Alembic**: Herramienta de migración que mantiene el esquema sincronizado para bases de datos relacionales.

#### Herramientas de Desarrollo
- **Docker**: Containerización que facilita la reproducibilidad del entorno y desarrollo local completo.
- **Docker Compose**: Orquestación local que permite ejecutar todo el stack con un solo comando.
- **GitHub Actions**: CI/CD que automatiza validaciones y despliegues.

### Justificación de Elecciones

#### FastAPI + SQLModel + Pydantic
Esta combinación proporciona:
- **DTOs unificados**: Modelos que sirven para persistencia, validación y transferencia de datos.
- **Documentación automática**: OpenAPI/Swagger generado automáticamente.
- **Validación en tiempo de ejecución**: Contratos verificables que actúan como documentación viva.
- **Compatibilidad con IA**: Estructuras claras que facilitan la comprensión y modificación.

#### React + TypeScript
- **Componentes reutilizables**: Patrones establecidos que la IA puede reconocer y aplicar.
- **Tipado estático**: Mejora la comprensión del código y reduce errores.
- **Ecosistema maduro**: Herramientas y librerías bien documentadas.
- **Desarrollo local**: Hot reload y herramientas de desarrollo que facilitan la iteración rápida.

#### Docker + Docker Compose
- **Entorno reproducible**: Garantiza que el desarrollo local sea idéntico al de producción.
- **Stack completo local**: Permite ejecutar toda la aplicación (frontend, backend, base de datos) con un solo comando.
- **Feedback inmediato**: Los agentes pueden probar cambios instantáneamente usando curl, terminal o herramientas MCP.

---

## Estructura del Proyecto

### Principios de Organización

1. **Reducción de Fricción**: Minimizar la necesidad de reuniones de contexto y alineación.
2. **Vertical Slices**: Agrupar funcionalidades relacionadas en módulos cohesivos.
3. **Monorepo**: Mantener frontend y backend en el mismo repositorio para reducir interfaces.
4. **Contexto Completo**: Proporcionar toda la información necesaria para que los agentes trabajen efectivamente.
5. **Desarrollo Local Completo**: Todo el stack debe poder ejecutarse localmente para facilitar el lazo de feedback inmediato que permite a los agentes evaluar resultados mediante herramientas como curl, terminal o MCP e iterar rápidamente.

### Organización por Dominios

En lugar de separar por capas técnicas (controllers, services, models), organizar por dominios de negocio:

```
src/
├── domains/
│   ├── users/
│   │   ├── models/
│   │   ├── services/
│   │   ├── controllers/
│   │   ├── tests/
│   │   └── README.md
│   ├── payments/
│   │   ├── models/
│   │   ├── services/
│   │   ├── controllers/
│   │   ├── tests/
│   │   └── README.md
│   └── listings/
│       ├── models/
│       ├── services/
│       ├── controllers/
│       ├── tests/
│       └── README.md
├── shared/
│   ├── database/
│   ├── auth/
│   ├── utils/
│   └── types/
└── frontend/
    ├── components/
    ├── pages/
    └── hooks/
```

### Ventajas de Vertical Slices

1. **Contexto Completo**: Todo lo necesario para una funcionalidad está en un lugar.
2. **Reducción de Dependencias**: Menos necesidad de navegar entre múltiples archivos.
3. **Trabajo Paralelo**: Equipos pueden trabajar en dominios diferentes sin conflictos.
4. **Compatibilidad con IA**: Los agentes pueden comprender y modificar funcionalidades completas.
5. **Testing Local**: Facilita la ejecución de pruebas completas del dominio en el entorno local.

### Metadatos para IA

Cada archivo debe incluir metadatos estructurados que faciliten la comprensión por agentes de IA:

```typescript
/**
 * @scope: api, cli, test
 * @slice: users, payments, invoices, listings
 * @layer: controller, application, model, view, helper, command
 * @type: usecase, service, gateway, test, orm
 */
```

### Convenciones de Nomenclatura

1. **Consistencia**: Usar patrones predecibles en nombres de archivos y funciones.
2. **Descriptividad**: Nombres que comuniquen claramente el propósito.
3. **Evitar Abreviaciones**: Usar nombres completos que no requieran contexto adicional.

---

## Integración con Documentación de Arquitectura

### ADRs (Architecture Decision Records)

Los ADRs capturan el "por qué" de las decisiones arquitectónicas:

- **Formato mínimo útil**: Contexto → Decisión → Alternativas → Consecuencias.
- **Ubicación**: `/docs/adr` o `/architecture/decisions`.
- **Beneficio para IA**: Proporciona contexto histórico para evitar cambios que rompan supuestos críticos.

### Documentación Viva

La documentación debe evolucionar junto con el código:

1. **Automatización**: CI que advierte sobre cambios sin actualizaciones de documentación.
2. **Enlaces Directos**: Referencias desde código a documentación relevante.
3. **Búsqueda Semántica**: Documentación indexada y fácilmente navegable.
4. **Actualización Continua**: Este documento de arquitectura debe actualizarse siempre que sucedan cambios, siendo la fuente de verdad en cuanto a componentes e interacciones con sistemas externos (C4 nivel 1 y 2) así como del lenguaje ubicuo.

### Validación Automatizada

Implementar validaciones que aseguren:

- **Convenciones de nombres**: Adherencia a patrones establecidos.
- **Documentación de PII**: Campos sensibles documentados según `security.md`.
- **Relaciones**: Claves foráneas con documentación explícita.
- **Metadatos**: Presencia de tags necesarios para IA.
- **Entorno Local**: Verificación de que todos los componentes pueden ejecutarse localmente.
- **Actualización de Documentación**: Alertas cuando cambios en el código requieren actualización de la documentación de arquitectura.

---

## Conclusión

Esta filosofía de arquitectura reconoce que la compatibilidad con agentes de IA es un criterio de diseño fundamental. Al diseñar sistemas que faciliten el trabajo conjunto entre humanos y IA, no solo mejoramos la productividad del desarrollo, sino que también creamos sistemas más mantenibles, documentados y alineados con las mejores prácticas de la industria.

Los principios establecidos aquí deben guiar todas las decisiones arquitectónicas del proyecto, asegurando que el sistema evolucione de manera coherente y que tanto humanos como agentes de IA puedan contribuir efectivamente a su desarrollo y mantenimiento.

**Puntos clave para recordar:**
- **Desarrollo local completo** es fundamental para el lazo de feedback inmediato que permite a los agentes iterar rápidamente.
- **Este documento de arquitectura debe actualizarse siempre** que sucedan cambios, siendo la fuente de verdad en cuanto a componentes e interacciones con sistemas externos (C4 nivel 1 y 2) así como del lenguaje ubicuo.
