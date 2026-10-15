# Security guidelines

## 1. Propósito

Definir las políticas y prácticas de seguridad que deben seguirse **al desarrollar código** en este
proyecto, tanto por personas como por copilotos, garantizando que la generación de software sea
segura por defecto y compatible con los estándares de Habi.

## 2. Alcance

Aplica a:

- Todo el código, configuraciones y datos presentes en este repositorio.
- Código, prompts y outputs generados o modificados por copilotos de IA.
- Scripts, definiciones IaC y configuraciones que gestionen recursos de AWS y GCP.

## 3. Logging seguro

- No incluir credenciales, tokens, PII ni datos financieros en logs en ningún nivel (`DEBUG`,
  `INFO`, `WARN`, `ERROR`).
- Los mensajes de error visibles a cliente deben ser genéricos. Los detalles técnicos van solo a
  logs internos filtrando campos sensibles.
- En AWS, enviar logs a **CloudWatch** con filtros para excluir campos sensibles.  
  En GCP, enviar logs a **Cloud Logging** aplicando anonimización previa.
- Mantener una lista de campos sensibles prohibidos de loggear y aplicarla en validaciones de CI.
- **Recomendación**: fomentar el _logging estructurado_ (JSON u otro formato parseable) para
  facilitar filtrado, búsqueda y alertas automáticas.

  Ejemplo:

  ```json
  { "event": "login_failure", "userId": "abc123", "level": "WARN" }
  ```

  en lugar de texto plano como `User abc123 failed to log in`.  
  El copiloto debe preferir este formato por defecto.
- Bajo ninguna circunstancia se deben incluir credenciales, claves API, tokens u otros secretos (AWS, GCP u otros proveedores) en las salidas de registro, ya sea mediante print o herramientas de logging.

- Los secretos deben ser utilizados exclusivamente por la aplicación en tiempo de ejecución y nunca ser expuestos en texto plano en archivos de log

## 4. Manejo de credenciales y secretos

- **Prohibido** incluir credenciales o contraseñas en código fuente, ejemplos, documentación o
  prompts.
- Usar un gestor seguro de secretos (AWS Secrets Manager, SSM Parameter Store, GCP Secret Manager).
- Variables de entorno declaradas en `.env.example` sin valores reales.
- Si un copiloto detecta un secreto en un prompt o en código, debe **alertar** y solicitar rotación
  inmediata según procedimiento oficial.
- **Escaneo proactivo de secretos**: integrar herramientas como `gitleaks` o `trufflehog` en hooks
  pre-commit para impedir commits con secretos.
- Los archivos .env que contengan credenciales o configuraciones sensibles deben estar incluidos
  en el .gitignore para evitar su inclusión en el control de versiones.
- Únicamente se podrán versionar archivos .env de referencia para entornos de desarrollo local,
  tales como local.env o template.env, sin incluir valores reales de credenciales.

- Únicamente se podrán versionar archivos .env de referencia para entornos de desarrollo local, tales como local.env o template.env, sin incluir valores reales de credenciales.

## 5. Protección y manejo de PII

- Los campos PII se documentan en `DATABASE.md`.  
  El copiloto y el desarrollador deben **leer** este archivo para identificar y tratar estos campos
  con sensibilidad.
- Prohibido exponer PII en logs, mensajes de error, respuestas de API o salidas de consola.
- Anonimizar o enmascarar PII antes de enviarla a servicios externos o dashboards.
- Usar cifrado en reposo y en tránsito (TLS 1.2+) al manipular PII.

## 6. Validación y sanitización de datos

- Validar **todas** las entradas externas: APIs, formularios, archivos, parámetros de línea de
  comandos.
- Usar tipado fuerte, validación de esquema y expresiones regulares seguras.
- Escapar y sanear salidas antes de insertarlas en HTML, SQL, JSON, XML u otros contextos
  interpretados.
- Limitar tamaño de payloads y tiempos de ejecución.
- **Principio de "Denegar por Defecto"**: validar usando _listas blancas_ (permitir solo formatos
  conocidos/seguros) en lugar de listas negras.
- **Protección contra Asignación Masiva**: al deserializar datos (por ejemplo, JSON a objetos), usar
  DTOs o definir explícitamente qué campos son asignables para evitar la modificación de campos
  internos como `isAdmin` o `accountBalance`.

## 7. Uso seguro de SDKs y APIs cloud

- **AWS S3 / GCP Cloud Storage**:
  - Forzar cifrado en reposo (`SSE-KMS` o CMEK) y en tránsito (HTTPS).
  - No permitir ACLs públicas (`public-read`, `allUsers`) sin aprobación explícita.
- **AWS RDS / GCP Cloud SQL / BigQuery**:
  - Conexiones solo con TLS/SSL (`require_secure_transport`, `sslmode=require`).
  - Credenciales siempre desde Secret Manager.
  - No exponer datos sensibles en consultas registradas.
- Endpoints generados (APIs, Lambdas, Cloud Functions) deben incluir autenticación por defecto y
  CORS restrictivo.
- Las políticas S3 de IAM para CloudFront deben ser gestionadas exclusivamente por un OAI, OAO
  o OAC autorizado.
- Está estrictamente prohibido el uso de comodines ("*") en los atributos "Action" o "Effect" de
  las políticas, salvo que estén acompañados de un ARN específico y validado.
- El uso de la cuenta raíz (root account) está prohibido para la asignación de permisos.
- Las credenciales de RDS para usuarios o servicios de AWS deben gestionarse exclusivamente a
  través de IAM.
- Solo en casos excepcionales (servicios de terceros o requisitos especiales) se podrán utilizar
  contraseñas, las cuales deberán almacenarse siempre en un servicio de gestión de secretos como
  AWS Secrets Manager o su equivalente en GCP (Secret Manager).

## 8. Adherencia a prácticas seguras de desarrollo

El proyecto debe cumplir **obligatoriamente** con:

- **OWASP Top 10 (Web y API)**: Controles aplicables a inyección, autenticación, control de acceso,
  exposición de datos sensibles y uso de componentes seguros.
- **OWASP ASVS v4.x – Nivel 2**: Controles aplicables a validación de entrada, escape de salida,
  gestión de sesiones y protección de datos en tránsito y reposo.
- **CWE Top 25**: Prevención de las vulnerabilidades más comunes y críticas.

### Uso de dependencias seguras

- El copiloto debe sugerir versiones sin CVEs conocidos.
- Merge bloqueado si SCA detecta vulnerabilidades críticas.
- Uso y versionado obligatorio de archivos de bloqueo (`package-lock.json`, `poetry.lock`, `go.sum`)
  para asegurar builds reproducibles.

### Seguridad de la Cadena de Suministro (SSCS)

- **Selección de dependencias**: el desarrollador es responsable de elegir librerías y frameworks de
  terceros priorizando componentes con historial de seguridad limpio y sin vulnerabilidades
  conocidas.
- **Gestión de dependencias**: mantener actualizados los archivos de bloqueo para asegurar
  reproducibilidad y seguridad. No deshabilitar los escaneos de vulnerabilidades en el entorno
  local.
- **Generación de SBOM**: generar una lista de materiales de software (SBOM) para cada artefacto del
  proyecto, proporcionando visibilidad completa de todos los componentes y sus licencias. La
  generación puede automatizarse desde el entorno local o en CI, pero el desarrollador debe
  verificar su existencia y exactitud.

## 9. Gestión de incidentes

- Toda detección de exposición de secretos o PII debe generar alerta y activar el procedimiento de
  respuesta en menos de 30 minutos.
- Documentar el incidente y las acciones correctivas en el sistema oficial de incidentes.
- El copiloto debe sugerir correcciones inmediatas al detectar incumplimientos.

## 10. Seguridad en CI/CD

- Los pipelines no deben ejecutar scripts de Bash, Python u otros lenguajes de forma dinámica
  durante su ejecución, salvo que cuenten con validación previa del equipo de DevSecOps.
- Los scripts o la lógica de negocio no deben alterar, modificar o eliminar recursos de
  infraestructura, red o servicios en AWS, GCP, Azure, Cloudflare, MongoDB u otros proveedores.
- Las modificaciones a la infraestructura deben realizarse exclusivamente mediante
  Infraestructura como Código (IaC).