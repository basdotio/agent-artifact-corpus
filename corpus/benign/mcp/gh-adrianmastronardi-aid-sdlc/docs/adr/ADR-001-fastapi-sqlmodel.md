# ADR-001: Uso de FastAPI + SQLModel para Backend

## Estado
Aceptado

## Fecha
2024-12-19

## Participantes
- Equipo de Arquitectura
- Equipo de Backend
- Equipo de DevOps

## Contexto

Siguiendo la filosofía de arquitectura establecida en `architecture-philosophy.md`, necesitamos seleccionar un stack de backend que cumpla con los principios fundamentales:

1. **Frameworks opinados**: Preferir tecnologías que impongan estructura coherente y predecible
2. **Compatibilidad con IA**: Frameworks que faciliten la comprensión y modificación por agentes de IA
3. **Desarrollo local completo**: Todo el stack debe poder ejecutarse localmente para facilitar el lazo de feedback inmediato
4. **Reducción de fricción cognitiva**: Minimizar la carga cognitiva tanto para humanos como para agentes de IA

El backend debe proporcionar:
- APIs REST predecibles y bien documentadas
- Validación robusta de datos
- Integración fluida con bases de datos relacionales
- Generación automática de documentación
- Testing eficiente y local

## Decisión

Implementar el backend usando **FastAPI + SQLModel + Pydantic** como stack principal.

### FastAPI como Framework Web
- **Versión**: 0.104.x o superior
- **Justificación**: Framework moderno, rápido y con documentación automática
- **Características clave**:
  - Generación automática de OpenAPI/Swagger
  - Validación automática de tipos con Pydantic
  - Soporte nativo para async/await
  - Testing integrado con TestClient
  - Middleware extensible para formateo de respuestas

### SQLModel como ORM
- **Versión**: 0.0.14 o superior
- **Justificación**: Combina SQLAlchemy y Pydantic en una sola librería
- **Características clave**:
  - Modelos unificados para API y base de datos
  - Compatibilidad total con SQLAlchemy
  - Validación automática con Pydantic
  - Migraciones con Alembic
  - Type hints completos para TypeScript

### Pydantic para Validación
- **Versión**: 2.x
- **Justificación**: Validación robusta y serialización eficiente
- **Características clave**:
  - Validación en tiempo de ejecución
  - Serialización/deserialización automática
  - Generación de esquemas JSON
  - Validadores personalizables
  - Compatibilidad con FastAPI

## Consecuencias

### Positivas
1. **DTOs unificados**: Modelos que sirven para persistencia, validación y transferencia de datos
2. **Documentación automática**: OpenAPI/Swagger generado automáticamente
3. **Validación en tiempo de ejecución**: Contratos verificables que actúan como documentación viva
4. **Compatibilidad con IA**: Estructuras claras que facilitan la comprensión y modificación
5. **Desarrollo local**: Hot reload y herramientas de desarrollo que facilitan la iteración rápida
6. **Testing eficiente**: TestClient integrado para testing de APIs
7. **Performance**: FastAPI es uno de los frameworks Python más rápidos

### Negativas
1. **Curva de aprendizaje**: SQLModel es relativamente nuevo y puede requerir familiarización
2. **Ecosistema**: Menos maduro que Django o Flask
3. **Dependencias**: Requiere Python 3.8+ y dependencias específicas
4. **Debugging**: Algunas herramientas de debugging pueden no estar optimizadas

### Mitigaciones
1. **Documentación**: Crear guías de desarrollo y ejemplos
2. **Testing**: Implementar tests exhaustivos para validar comportamiento
3. **Monitoreo**: Implementar logging y observabilidad robusta
4. **Comunidad**: Participar en la comunidad de FastAPI y SQLModel

## Alternativas Consideradas

### 1. Django + Django REST Framework
- **Pros**: Muy maduro, admin automático, ORM robusto
- **Contras**: Más pesado, menos flexible, curva de aprendizaje más pronunciada
- **Decisión**: Rechazado por complejidad y falta de flexibilidad

### 2. Flask + SQLAlchemy
- **Pros**: Ligero, flexible, maduro
- **Contras**: Requiere más configuración manual, menos opinado
- **Decisión**: Rechazado por falta de estructura opinada

### 3. FastAPI + SQLAlchemy + Pydantic
- **Pros**: Flexibilidad total, control granular
- **Contras**: Más código boilerplate, duplicación de modelos
- **Decisión**: Rechazado por SQLModel proporciona mejor integración

## Implementación

### Fase 1: Configuración Base (Sprint 1)
1. Configurar entorno de desarrollo con Docker
2. Implementar estructura base del proyecto
3. Configurar FastAPI con middleware básico
4. Configurar SQLModel con PostgreSQL

### Fase 2: Modelos y Validación (Sprint 2)
1. Implementar modelos base con SQLModel
2. Configurar Pydantic para validación
3. Implementar esquemas de respuesta estándar
4. Configurar Alembic para migraciones

### Fase 3: APIs y Testing (Sprint 3)
1. Implementar endpoints REST básicos
2. Configurar TestClient para testing
3. Implementar validación de entrada
4. Generar documentación OpenAPI

### Fase 4: Integración y Optimización (Sprint 4)
1. Integrar con frontend
2. Optimizar performance
3. Implementar logging y monitoreo
4. Documentar patrones de uso

### Estructura de Implementación
```
src/
├── main.py                 # Punto de entrada FastAPI
├── config/
│   ├── __init__.py
│   ├── database.py        # Configuración de base de datos
│   └── settings.py        # Variables de entorno
├── shared/
│   ├── database/
│   │   ├── __init__.py
│   │   └── connection.py  # Configuración SQLModel
│   ├── api/
│   │   ├── __init__.py
│   │   └── response.py    # Formateo de respuestas
│   └── utils/
│       ├── __init__.py
│       └── validators.py  # Validadores personalizados
└── domains/
    └── [dominio]/
        ├── models.py       # Modelos SQLModel
        ├── schemas.py      # Esquemas Pydantic
        └── api.py          # Endpoints FastAPI
```

Este ADR establece FastAPI + SQLModel + Pydantic como la base tecnológica del backend, proporcionando una estructura opinada, predecible y compatible con agentes de IA, facilitando el desarrollo local completo y el lazo de feedback inmediato que es fundamental para la filosofía de arquitectura establecida.
