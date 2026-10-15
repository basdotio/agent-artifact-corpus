# Gestión de Secretos y Credenciales

La protección de credenciales es la primera línea de defensa para nuestros sistemas.

Prohibición de Credenciales Quemadas: Está estrictamente prohibido incrustar o "quemar" cualquier tipo de credencial (claves de API, contraseñas, tokens) directamente en el código fuente.

Gestor de Secretos Centralizado: Todas las credenciales deben ser gestionadas a través de un servicio seguro como Google Secret Manager. La aplicación recuperará estos secretos en tiempo de ejecución, nunca durante el proceso de construcción (build).

Generación Segura: Las claves, como la API_KEY del servicio, se generan de forma segura y aleatoria durante el despliegue a través de Pulumi, como se observa en el fichero iac/__main__.py, asegurando que sean únicas para cada entorno.

## Seguridad de Infraestructura y Entornos

La segregación de entornos es fundamental para prevenir que los problemas de un ambiente afecten a otro.

Separación por Proyecto de GCP: Cada entorno (ej. desarrollo, QA, producción) debe estar desplegado en su propio proyecto de Google Cloud Platform. Esto garantiza un aislamiento completo de recursos, redes y permisos.

Nomenclatura Estándar: Los proyectos seguirán una nomenclatura clara que identifique su propósito y entorno, como por ejemplo: xx-main-qa y xx-main-prod.

Identidad y Gestión de Accesos (IAM) identidade
El acceso a los recursos de la nube debe ser controlado y limitado rigurosamente.

Principio de Mínimo Privilegio: Todas las cuentas, tanto de usuario como de servicio, deben operar bajo este principio. Se les otorgarán únicamente los permisos estrictamente necesarios para realizar sus funciones designadas.

Uso de Roles Predefinidos: Para la gestión de permisos en GCP, se priorizará el uso de los roles predefinidos de Google Cloud. Esto asegura que los permisos son gestionados y mantenidos por Google, reduciendo el riesgo de configuraciones erróneas. Se crearán roles personalizados solo cuando sea absolutamente necesario y con la debida justificación.

Cuentas de Servicio Dedicadas: Cada servicio (como el Cloud Run principal o los jobs programados) debe tener su propia cuenta de servicio dedicada (ej: {resource_name}-sa). Esto permite asignarles permisos granulares sin afectar a otros componentes.

## Seguridad del Código y Dependencias

La seguridad debe estar integrada en el ciclo de vida del desarrollo de software (DevSecOps).

Análisis Estático de Seguridad (SAST): Se realizarán escaneos de vulnerabilidades en el código fuente de manera regular utilizando herramientas como Sonar. Los resultados de estos análisis deben ser revisados y las vulnerabilidades críticas deben ser resueltas antes de desplegar en producción.

Gestión de Dependencias (SCA): Las dependencias de terceros, listadas en archivos como requirements.txt, deben ser monitoreadas continuamente en busca de vulnerabilidades conocidas.

Seguridad de Contenedores: Las imágenes base de Docker (ej: python:3.11.8-slim) deben ser escaneadas en busca de vulnerabilidades y actualizadas a versiones seguras de forma periódica.
