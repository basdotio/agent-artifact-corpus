# Deployment

Este documento detalla los pasos, entornos, herramientas y validaciones necesarias para realizar un despliegue seguro y controlado de la aplicación y su infraestructura.

## Estrategia de Ramas y Entornos

Nuestro flujo de trabajo se basa en una estrategia de ramas que se mapea directamente a nuestros entornos en Google Cloud Platform. Esto garantiza un ciclo de vida de desarrollo y despliegue predecible.

### Entorno de QA (Calidad)

Rama: develop

Proyecto GCP: xx-main-qa

Propósito: Este entorno se utiliza para la validación de nuevas funcionalidades y para la ejecución de pruebas de integración sobre los servicios recién desplegados.

### Entorno de Producción

Rama: master

Proyecto GCP: xx-main-prod

Propósito: Es el entorno final que sirve a los usuarios. Solo el código que ha sido validado y aprobado puede llegar aquí.

## Pipeline de Despliegue (CI/CD)

Todo el proceso de despliegue está orquestado por GitLab CI/CD. El pipeline consta de una serie de etapas secuenciales y bloqueantes, lo que significa que el fallo en una etapa detiene todo el proceso para prevenir errores.

### Etapa 1: Pruebas y Análisis de Calidad (Bloqueante)

Disparador: Se ejecuta en cada commit a las ramas develop y master.

Acciones:

Linters y Formateadores: Se ejecutan herramientas como flake8 y pylint para asegurar la consistencia y calidad del código.

Análisis de Seguridad: Sonar escanea el código en busca de vulnerabilidades de seguridad y "code smells".

Pruebas Unitarias y Cobertura: Se ejecutan las pruebas unitarias y se valida que el código nuevo cumpla con el umbral del 80% de cobertura.

Resultado: Si alguna de estas validaciones falla, el pipeline se detiene y no se procede al despliegue.

### Etapa 2: Análisis de Seguridad con SonarQube (Bloqueante)

Disparador: Se ejecuta si la Etapa 1 es exitosa.

Acción: SonarQube escanea el código en busca de vulnerabilidades de seguridad, "code smells" y bugs.

Resultado: El pipeline se detiene si se detectan problemas que no cumplen con el umbral de calidad (Quality Gate) definido en SonarQube.

### Etapa 3: Despliegue con Pulumi (Bloqueante)

Disparador: Se ejecuta automáticamente si la Etapa 1 es exitosa.

Acción: Se invoca a Pulumi para que sincronice el estado de la infraestructura definido en el código (carpeta iac/) con el entorno de GCP correspondiente. Pulumi se encarga de crear, actualizar o eliminar los recursos necesarios (Cloud Run, Schedulers, etc.) y desplegar la nueva versión de la aplicación.

### Etapa 4: Pruebas de Integración (Post-Despliegue)

Disparador: Se ejecuta después de un despliegue exitoso en el entorno de QA (develop).

Acción: Se lanza un conjunto de pruebas de integración que validan el comportamiento del servicio desplegado en un entorno real.

Nota: Actualmente, este paso solo aplica para los componentes de tipo "servicio" y se considera una validación adicional.
