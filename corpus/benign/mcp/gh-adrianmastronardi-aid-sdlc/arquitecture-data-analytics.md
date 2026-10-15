# Arquitectura

Este proyecto despliega una aplicación de MLOps en GCP. La infraestructura está completamente definida y gestionada con Pulumi en Python. El sistema se compone principalmente de dos tipos de cargas de trabajo contenerizadas que se ejecutan de forma serverless en Google Cloud Run:

Un servicio web (API) persistente, construido con FastAPI.

Un trabajo o tarea programada (cron job) que ejecuta un proceso específico de forma periódica.

Todo el código, tanto de la aplicación como de la infraestructura, está organizado en un monorepositorio, facilitando su gestión y versionado.

## Descripción General del Sistema

Este proyecto despliega una aplicación de MLOps en GCP. La infraestructura está completamente definida y gestionada con Pulumi en Python. El sistema se compone principalmente de dos tipos de cargas de trabajo contenerizadas que se ejecutan de forma serverless en Google Cloud Run:

Un servicio web (API) persistente, construido con FastAPI.

Un trabajo o tarea programada (cron job) que ejecuta un proceso específico de forma periódica.

Todo el código, tanto de la aplicación como de la infraestructura, está organizado en un monorepositorio, facilitando su gestión y versionado.

## Componentes y Estructura

EL sistema se compone de los siguientes recursos principales en GCP, todos ellos creados y configurados desde el código de Pulumi (iac/__main__.py):

Artifact Registry: Actúa como tu registro privado de Docker. Aquí es donde se almacenan las imágenes de contenedor de tu API y de tus trabajos programados después de ser construidas.

Cloud Run Service: Es el componente que ejecuta tu API de FastAPI de forma continua. Se configura para ser accesible públicamente (o a través de una URL interna) y se le asignan variables de entorno, como API_KEY y la URL del propio servicio.

Cloud Run Job: Ejecuta tareas específicas que tienen un inicio y un fin. En tu caso, se usa para los "features", como el cron-feature definido en src/features/config.yaml. Estos trabajos se configuran con sus propios recursos (CPU, memoria) y cuenta de servicio.

Cloud Scheduler: Es el "cron" de GCP. Se utiliza para invocar al Cloud Run Job en una agenda específica (definida por la expresión schedule en los archivos de configuración).

Service Accounts (IAM): Creas cuentas de servicio dedicadas para tus componentes de Cloud Run (-sa). Esto es una excelente práctica de seguridad, ya que permite otorgar permisos granulares a cada servicio según sus necesidades (Principio de Mínimo Privilegio). Los roles se asignan dinámicamente desde diccionarios en el código.

Cloud Storage: Creas una carpeta gestionada (ManagedFolder) dentro de un bucket de Cloud Storage. Esto sugiere que tus servicios pueden necesitar leer o escribir archivos de forma persistente.

Cloud Monitoring (Alerts): Defines políticas de alerta, por ejemplo, para notificar si el número de instancias de un Cloud Run Service supera un umbral. Esto es clave para la observabilidad y la fiabilidad del sistema.

## Flujo de Despliegue y CI/CD

Activación del Pipeline: Un push a una rama como develop o master inicia el pipeline de CI/CD.

Construcción de Imágenes:

El pipeline construye una imagen de Docker para la API principal usando el Dockerfile de la raíz.

También construye una imagen para el "feature" (el trabajo programado) usando el src/features/Dockerfile.

Publicación en Artifact Registry: Las imágenes construidas se etiquetan y se suben a tu repositorio en Artifact Registry.

Despliegue con Pulumi:

El pipeline ejecuta pulumi up dentro del directorio iac.

Pulumi lee el estado actual de la infraestructura en GCP.

Detecta que las imágenes de Docker han sido actualizadas y crea una nueva revisión del Cloud Run Service y/o actualiza el Cloud Run Job para usar la nueva imagen.

Aprovisiona o actualiza cualquier otro recurso definido (Scheduler, Service Accounts, etc.).

Actualización de Variables: Al final del despliegue, el script de Pulumi actualiza variables de CI/CD en GitLab (como SRV_URL y KEY_URL) con los valores de la infraestructura desplegada (la URL del servicio y la API key generada).

## Decisiones Técnicas Clave

Infraestructura como Código con Python
Serverless y Contenedores
Separación de Servicios y Trabajos
Configuración Dinámica: El código de Pulumi lee archivos de configuración (.yaml) para definir el comportamiento de los recursos, como la programación del cron o los roles IAM a asignar.
