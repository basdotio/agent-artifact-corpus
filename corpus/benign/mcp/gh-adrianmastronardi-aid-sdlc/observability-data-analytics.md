# Filosofía de Observabilidad

Nuestra estrategia se centra en la acción y la relevancia. No buscamos medirlo todo, sino monitorear las señales vitales que nos permitan detectar problemas, diagnosticar sus causas y responder a ellos de manera efectiva. Utilizamos las herramientas nativas de Google Cloud Platform para centralizar nuestra observabilidad.

## Monitoreo y Métricas Clave

Herramienta: Google Cloud Logging.

### Errores

Descripción: Monitoreamos activamente los logs en busca de entradas con severidad ERROR. Este es nuestro principal indicador de que algo está funcionando mal en la aplicación. La política de alerta específica para esto se define en la sección de Alertas.

### Latencia

Descripción: Se monitorea el tiempo de respuesta de las peticiones a nuestros servicios. Una latencia elevada es un indicador clave de degradación del rendimiento o de problemas inminentes.

## Gestión de Alertas

### Alerta de Tasa de Errores

Condición: Se dispara una alerta si se registran 10 o más eventos de log con severidad "ERROR" en el transcurso del mismo día.

Fuente: Definida en el código de infraestructura iac/pulumi_resources/alert_policy.py.

### Alerta de Alta Latencia

Condición: Se dispara una alerta para cualquier petición que tarde más de 30 segundos en completarse.

## Dashboards y Visualización

Herramienta Principal: Google Cloud Monitoring Dashboards.

Para la visualización del estado del sistema, utilizamos los paneles predeterminados que Google Cloud proporciona para servicios como Cloud Run. Estos dashboards son el punto de partida para cualquier investigación visual del rendimiento del servicio

## Métricas de Negocio

La implementación de métricas específicas de negocio sigue un proceso de planificación estricto para asegurar que cada métrica tenga un propósito claro y un resultado esperado.

Proceso de Definición: Antes de implementar cualquier métrica de negocio (ej: "procesos completados por hora"), es requisito indispensable tener una sesión de planificación con el Director de Analítica. En esta sesión, se define el plan, el resultado esperado y cómo se visualizará.

Política: No se despliegan métricas de negocio a producción si no han pasado por este proceso de validación y planificación estratégica
