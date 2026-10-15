# Filosofía y Responsabilidades

La calidad del software es una responsabilidad compartida, pero la implementación de las pruebas recae directamente en los desarrolladores. Nuestro enfoque se basa en el principio de que quien construye una funcionalidad es la persona más indicada para construir también su red de seguridad a través de pruebas automatizadas.

Responsable Principal: Cada desarrollador es responsable de escribir las pruebas para el código que produce. Esto incluye pruebas unitarias y, cuando sea aplicable, pruebas de integración.

Momento de Escritura: Las pruebas deben ser escritas durante la fase de desarrollo de una nueva funcionalidad o de la corrección de un error. Lo ideal es que el código y sus pruebas se entreguen juntos en el mismo Merge Request (MR) para asegurar que todo nuevo aporte al repositorio esté debidamente validado.

## Estándares de Calidad y Cobertura

Para garantizar un nivel de calidad consistente y evitar la degradación del código, se establece un estándar de cobertura mínimo.

Métrica de Cobertura: La cobertura de pruebas se mide por el número de líneas de código ejecutables que son alcanzadas por las pruebas automatizadas.

Requisito de Cobertura:

Para código nuevo: Se exige una cobertura mínima del 80% en todas las nuevas funcionalidades o archivos añadidos al proyecto.

Comportamiento en Merge Requests: Si un MR disminuye la cobertura general del proyecto, el pipeline mostrará una advertencia. Aunque no bloqueará la fusión, se espera que el equipo revise el caso y justifique la disminución. No se debe permitir que la deuda técnica en pruebas se acumule.

## Herramientas y Automatización

Se ha definido un conjunto de herramientas estándar para mantener la consistencia en el desarrollo y ejecución de las pruebas.

Frameworks de Pruebas: Se utilizarán los frameworks Pytest y Unittest para la escritura de las pruebas. Pytest es preferido por su sintaxis concisa y su potente sistema de fixtures.

Mocks y Dobles de Prueba: Para aislar componentes y simular dependencias externas (como APIs o bases de datos), la librería recomendada es unittest.mock, que forma parte de la biblioteca estándar de Python.

Ejecución y CI/CD: La ejecución automatizada de todo el conjunto de pruebas se realiza en el pipeline de GitLab CI/CD con cada commit y merge request. Esto garantiza una retroalimentación rápida sobre la calidad del código.

## Convenciones y Buenas Prácticas

Para asegurar que las pruebas sean legibles, mantenibles y consistentes en todo el proyecto, se deben seguir las siguientes convenciones:

Nomenclatura de Archivos: Todos los archivos que contengan pruebas deben tener el prefijo test_. Por ejemplo: test_user_model.py.

Nomenclatura de Funciones: Todas las funciones de prueba dentro de esos archivos también deben comenzar con el prefijo test_. Por ejemplo: def test_create_user_successfully():.

Estructura de la Prueba: Se recomienda seguir el patrón Arrange-Act-Assert (AAA) para dar una estructura clara a cada prueba:

Arrange (Organizar): Configura las condiciones iniciales y las entradas de la prueba.

Act (Actuar): Ejecuta la función o el código que se está probando.

Assert (Afirmar): Verifica que el resultado o el estado final sea el esperado.
