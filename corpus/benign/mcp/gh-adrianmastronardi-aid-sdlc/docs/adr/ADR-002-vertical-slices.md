# ADR-002: Organización por Vertical Slices

## Estado
Aceptado

## Fecha
2024-12-19

## Participantes
- Equipo de Arquitectura
- Equipo de Desarrollo
- Equipo de QA

## Contexto

Siguiendo la filosofía de arquitectura establecida en `architecture-philosophy.md`, necesitamos definir la organización del código que cumpla con los principios fundamentales:

1. **Vertical slices sobre layering**: Agrupar todo lo necesario para una funcionalidad en un mismo módulo
2. **Reducción de fricción cognitiva**: Minimizar la carga cognitiva tanto para humanos como para agentes de IA
3. **Contexto completo**: Proporcionar toda la información necesaria para que los agentes trabajen efectivamente
4. **Desarrollo local completo**: Todo el stack debe poder ejecutarse localmente para facilitar el lazo de feedback inmediato
5. **Compatibilidad con IA**: Dominios que pueden ser comprendidos y modificados de forma independiente

La organización tradicional por capas técnicas (controllers, services, models) presenta problemas:
- Necesidad de navegar entre múltiples archivos para entender una funcionalidad
- Dependencias circulares entre capas
- Dificultad para trabajar en paralelo en diferentes funcionalidades
- Contexto fragmentado que dificulta el trabajo de agentes de IA

## Decisión

Implementar organización por **vertical slices** basada en dominios de negocio, donde cada slice contiene todos los elementos necesarios para una funcionalidad completa.

### Principios de Organización

1. **Cohesión funcional**: Funcionalidades que cambian por las mismas razones se agrupan juntas
2. **Acoplamiento mínimo**: Interfaces claras y estables entre dominios
3. **Contexto de negocio**: Alineación con conceptos del dominio de negocio
4. **Independencia**: Cada slice puede ser comprendido y modificado de forma independiente

### Estructura de Vertical Slices

```
src/
├── domains/
│   ├── users/                    # Slice de usuarios
│   │   ├── models/              # Modelos SQLModel
│   │   ├── services/            # Lógica de negocio
│   │   ├── api/                 # Endpoints FastAPI
│   │   ├── tests/               # Tests del dominio
│   │   └── README.md            # Documentación del dominio
│   ├── properties/              # Slice de propiedades
│   │   ├── models/              # Modelos de propiedades
│   │   ├── services/            # Servicios de propiedades
│   │   ├── api/                 # API de propiedades
│   │   ├── tests/               # Tests de propiedades
│   │   └── README.md            # Documentación de propiedades
│   └── payments/                # Slice de pagos
│       ├── models/              # Modelos de pagos
│       ├── services/            # Servicios de pagos
│       ├── api/                 # API de pagos
│       ├── tests/               # Tests de pagos
│       └── README.md            # Documentación de pagos
├── shared/                       # Recursos compartidos
│   ├── database/                # Configuración de base de datos
│   ├── auth/                    # Autenticación y autorización
│   ├── utils/                   # Utilidades comunes
│   └── types/                   # Tipos compartidos
└── frontend/                     # Aplicación frontend
    ├── components/               # Componentes React
    ├── pages/                    # Páginas de la aplicación
    └── hooks/                    # Hooks personalizados
```

### Contenido de Cada Slice

**Models (`models/`):**
- Entidades SQLModel del dominio
- Relaciones entre entidades
- Validaciones a nivel de modelo
- Migraciones específicas del dominio

**Services (`services/`):**
- Lógica de negocio del dominio
- Integración con sistemas externos
- Operaciones complejas que involucran múltiples modelos
- Reglas de negocio específicas

**API (`api/`):**
- Endpoints HTTP del dominio
- Validación de entrada
- Transformación de respuesta
- Autenticación y autorización específica

**Tests (`tests/`):**
- Tests unitarios de modelos
- Tests de servicios
- Tests de integración de API
- Fixtures y mocks del dominio

**README.md:**
- Descripción del dominio
- Casos de uso principales
- Dependencias con otros dominios
- Ejemplos de uso

## Consecuencias

### Positivas
1. **Contexto completo**: Todo lo necesario para una funcionalidad está en un lugar
2. **Reducción de dependencias**: Menos necesidad de navegar entre múltiples archivos
3. **Trabajo paralelo**: Equipos pueden trabajar en dominios diferentes sin conflictos
4. **Compatibilidad con IA**: Los agentes pueden comprender y modificar funcionalidades completas
5. **Testing local**: Facilita la ejecución de pruebas completas del dominio
6. **Mantenibilidad**: Cambios en un dominio no afectan otros dominios
7. **Onboarding**: Nuevos desarrolladores pueden entender un dominio completo rápidamente

### Negativas
1. **Duplicación potencial**: Algunas utilidades pueden duplicarse entre dominios
2. **Gobernanza**: Necesidad de definir claramente qué va en shared vs. dominio
3. **Refactoring**: Cambios que afectan múltiples dominios requieren coordinación
4. **Tamaño de slices**: Algunos dominios pueden crecer demasiado

### Mitigaciones
1. **Shared bien definido**: Solo código realmente común va en shared
2. **Interfaces claras**: Definir contratos entre dominios
3. **Refactoring incremental**: Cambios grandes se dividen en pasos pequeños
4. **Monitoreo de tamaño**: Alertas cuando un slice crece demasiado

## Alternativas Consideradas

### 1. Organización por Capas Técnicas
- **Pros**: Separación clara de responsabilidades técnicas
- **Contras**: Contexto fragmentado, dificulta trabajo paralelo
- **Decisión**: Rechazado por violar principio de contexto completo

### 2. Organización por Microservicios
- **Pros**: Independencia total entre servicios
- **Contras**: Complejidad de infraestructura, overhead de comunicación
- **Decisión**: Rechazado por complejidad excesiva para el proyecto actual

### 3. Organización por Funciones
- **Pros**: Agrupación lógica por funcionalidad
- **Contras**: Puede crear slices demasiado grandes o pequeños
- **Decisión**: Rechazado por falta de claridad en definición de funciones

## Implementación

### Fase 1: Definición de Dominios (Sprint 1)
1. Identificar dominios principales del negocio
2. Definir límites y responsabilidades de cada dominio
3. Crear estructura de directorios base
4. Documentar interfaces entre dominios

### Fase 2: Migración de Código Existente (Sprint 2-3)
1. Refactorizar código existente por dominios
2. Mover modelos, servicios y APIs a sus slices correspondientes
3. Actualizar imports y dependencias
4. Implementar interfaces entre dominios

### Fase 3: Testing y Validación (Sprint 4)
1. Implementar tests por dominio
2. Validar que cada slice es independiente
3. Verificar que shared no contiene lógica específica de dominio
4. Testing de integración entre dominios

### Fase 4: Documentación y Optimización (Sprint 5)
1. Crear README.md para cada dominio
2. Documentar patrones y convenciones
3. Optimizar estructura basada en feedback
4. Implementar validaciones automatizadas

### Herramientas de Validación
- **Scripts de estructura**: Verificar que archivos estén en ubicaciones correctas
- **Análisis de dependencias**: Identificar dependencias circulares
- **Métricas de tamaño**: Monitorear crecimiento de slices
- **Linting**: Verificar convenciones de nomenclatura por dominio

Este ADR establece la organización por vertical slices como el patrón arquitectónico principal, proporcionando contexto completo, reduciendo fricción cognitiva y facilitando el trabajo tanto de desarrolladores humanos como de agentes de IA, en línea con la filosofía de arquitectura establecida.
