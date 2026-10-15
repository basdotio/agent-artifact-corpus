# Testing Guidelines

## 1. Propósito

Definir las políticas y prácticas de testing que deben seguirse **al desarrollar código** en este
proyecto, tanto por personas como por copilotos, garantizando que la generación de software sea
segura por defecto y compatible con los estándares de Habi.

## 2. Proyectos a realizar

Aplica a:

- Solamente para la carpeta `tests/**` 
- Código, prompts y outputs generados o modificados por copilotos de IA.
- Archivos de configuración de testing y despliegue ya que estos definen los tests que usaremos
  - setup.cfg
  - .gitlab-ci.yml

## 3. Estructura de los tests en Python

## 3.1 Recomendaciones de los tests

- Realizar los tests con un título descriptivo
  - Deben estar escritas con la etiqueta `@pytest.mark` que exprese una descripción clara del objetivo de la prueba
- Genera documentación en el código de los tests para que **humanos y copilotos comprendan los tests que ya se están realizando**
- El coverage de las pruebas unitarias debe estar por encima del 80% y es de obligatoriedad mantenerlo.
- Reutilizar mocks y request a servicios grandes es primordial para mantener grandes sets de pruebas
- Tests independientes y deterministas
- Aserciones que generen valor para validar los diferentes casos de uso del componente:
  * Tipado de datos, validar el tipo de dato  ejemplo 1 != "1" debe fallar
  * Validar valores exactos y evitar usar assert con contains
  * Agregar el mayor número de validaciones que aseguren el funcionamiento del componente
- Mockea servicios de aws con la libreria `moto`

## 3.2 Datos de pruebas reutilizables con factories.

Para mantener los datos de prueba consistentes y reutilizables, se recomienda:

- Usar factories para generar datos de prueba realistas y aleatorios
- Centralizar la creación de datos en factories para evitar duplicación
- Parametrizar fixtures para probar múltiples escenarios
- Mantener los datos de prueba independientes entre tests
- Usar Faker para generar datos aleatorios válidos
- Documentar el propósito y estructura de cada factory

# Ejemplo:

```python
class UserFactory(factory.Factory):
    """
    Factory: User Test Data
    Purpose: Generate realistic user data for testing
    """
    class Meta:
        model = User
    
    username = factory.Faker("user_name")
    email = factory.Faker("email")
    password = factory.Faker("password")
    created_at = factory.LazyFunction(datetime.now)
```

### Fixtures Parametrizados

```python
@pytest.fixture(params=[
    ("admin", True),
    ("user", False),
    ("guest", False)
])
def user_role(request):
    """
    Fixture: User Roles
    Parameters:
    - role_name: str
    - has_admin: bool
    """
    return request.param
```

**Reutiliza asserts de servicios grandes, si contiene algún body de más de 30 parámetros es recomendable empezar
a centralizar y organizar según la estructura que a continuación se presenta

### 3.3 Organización de Directorios

```
tests/
├── __init__.py
├── conftest.py        # Configuración global de pytest
|__ mokcs/.py          # Mocks comunes
|   └── __init__.py
├── constants/         # Constantes para testing
│   └── __init__.py
├── factories/         # Factories para datos de prueba
│   └── __init__.py
├── fixtures/          # Fixtures reutilizables
│   └── __init__.py
├── integration/       # Tests de integración
│   └── __init__.py
├── unit/              # Tests unitarios
│   └── __init__.py
└── utils/             # Utilidades para testing
    └── __init__.py
```

Nomenclatura recomendada:

- Archivos: `test_<module_name>.py`
- Clases: `Test<ClassName>`
- Funciones: `test_<scenario>_<expected_result>`
- Fixtures: `<resource_type>_<state>`

### Librerías o Frameworks establecidos estándar para testing

El archivo `requirements.unittest.txt` contiene las dependencias necesarias para la correcta ejecución:

```txt
boto3                           # Cliente AWS oficial
moto==5.0.*                     # Mock de servicios AWS  
pytest==8.2.2                  # Framework de testing principal
pytest-mock==3.*               # Extensión para mocking
pytest-cov==5.0.0              # Cobertura de código
pytest-asyncio                 # Soporte para tests async
unittest-xml-reporting==3.2.0  # Reportes XML
coverage==7.5.3                # Análisis de cobertura
```


## 4 Advertencias para testing

- **NUNCA** 
  - usar `@pytest.mark.skip` - Todos los nuevos tests deben ejecutarse
  - Editar el coverage de los tests, siempre debe estar en 80% por estandares de habi
  Ejemplos:
    ### NO permitido:
    ```python
    @pytest.mark.skip("Reason")          # ❌ Nunca skipear tests
    @pytest.mark.xfail                   # ❌ No marcar como expected fail
    time.sleep()                         # ❌ No usar sleep en tests
    mock.patch.object(..., autospec=False) # ❌ Siempre usar autospec=True
    ```
## 5. Pasos para construir una prueba unitaria con un enfoque (TDD Opcional)

Sabiendo la estructura y buenas prácticas a seguir el paso a paso para construir una prueba unitaria
debe contener el siguiente paso a paso

- Evaluar los requerimientos del codigo segun la historia de usuario
- Evaluar el codigo existente para comprender la cobertura de los tests y no duplicar tests
- Definir los casos de prueba y escenarios a validar (happy path, edge cases, error cases)
- Generar los diferentes tests con las buenas practicas anteriormente recomendadas
- Implementar los mocks y fixtures necesarios para aislar las dependencias
- Proceso de iteración para tests fallidos: en medio de los tests fallidos debe contener una responsabilidad de no eliminar assert ni tests
- Refactorizar el código de prueba para mantener la legibilidad y evitar duplicación
- Validar la cobertura de código alcanzada (mínimo 80%)
- Cuando los tests finalicen haz un barrido de la documentación generada para el entendimiento futuro de los tests
- Ejecutar el conjunto completo de pruebas para validar que no hay regresiones
- Por último haz por segunda vez la validación de tests no repetidos para evitar un mantenimiento doloroso y el aumento de la ventana de contexto de los copilotos.

**Es importante mencionar que el proceso descrito anteriormente no requiere estrictamente seguir TDD (Test Driven Development). Es igualmente válido escribir el código primero y luego los tests. Lo fundamental es:

1. Evaluar cuidadosamente los requerimientos del negocio
2. Revisar la documentación existente del código
3. Agregar validación de valor según el código y los requerimientos de negocio.
4. Analizar los tests actuales para evitar duplicidad

Esto asegurará que los tests agreguen valor real y sean mantenibles a largo plazo tanto para humanos como copilotos**



## 5. Como implementar unit tests en servicios de aws con pytest

Los servicios de AWS son fundamentales en nuestra arquitectura y requieren una estrategia de testing robusta. La implementación de pruebas unitarias para servicios AWS no solo asegura la calidad del código, sino que también previene costos innecesarios y problemas en producción.

Esta guía aplica para una amplia gama de servicios AWS como:
- DynamoDB para pruebas de operaciones CRUD y consultas
- S3 para validación de operaciones con archivos y buckets
- SNS/SQS para mensajería y colas
- CloudWatch para logging y métricas
- EventBridge para eventos y triggers
- Step Functions para flujos de trabajo
- API Gateway para endpoints REST y WebSocket
- Cognito para autenticación y autorización

La clave está en utilizar moto y los mocks apropiados para simular estos servicios, permitiendo pruebas rápidas y confiables sin depender de recursos reales de AWS.

### 5.1 Tests de Lambda Functions

**Patrón obligatorio:**

```python
import json
import os
from types import SimpleNamespace
import pytest
from moto import mock_aws
from tests.lambda_mock import lambda_mock

@pytest.fixture
def event():
    """Define el evento de entrada de la lambda"""
    return {
        "Records": [{"body": json.dumps({"key": "value"})}],
        # O para HTTP:
        # "httpMethod": "GET",
        # "queryStringParameters": {"param": "value"},
        # "requestContext": {"authorizer": {"claims": {"email": "user@mail.com"}}}
    }

@mock_aws
@lambda_mock(
    container="src.lambdas.your_lambda.container",
    container_wrap=["service1", "service2"],  # Servicios a mockear
    load_env=True,                            # Cargar variables de entorno
    load_data=True,                          # Cargar datos de BD
    load_aws=True,                           # Cargar mocks AWS
    load_responses=True,                     # Cargar mocks HTTP
)
def test_lambda_handler(event, container=None):
    from src.lambdas.your_lambda.handler import lambda_handler as handler
    
    # Configuración adicional AWS si es necesario
    import boto3
    sns = boto3.client("sns", region_name="us-east-2")
    sns.create_topic(Name="test-topic.fifo", Attributes={"FifoTopic": "true"})
    
    # Ejecutar lambda
    response = handler(event, SimpleNamespace(aws_request_id="1234"))
    
    # Validaciones
    assert container.service1.method.call_count == 1
    assert response["statusCode"] == 200
```

El patrón mostrado arriba es esencial para garantizar pruebas consistentes y mantenibles. La estructura del mock_aws y lambda_mock facilita el aislamiento de componentes y la simulación precisa del entorno AWS. Esto permite probar diferentes escenarios y casos de error sin depender de recursos externos.

### 5.2 Tests con mocking de AWS Services


La inyección de dependencias es fundamental cuando trabajamos con servicios AWS, ya que nos permite:
- Aislar la lógica de negocio de la infraestructura AWS
- Facilitar el testing al poder mockear servicios complejos
- Mejorar la mantenibilidad al centralizar la configuración de servicios
- Permitir cambios en la implementación sin afectar la lógica de negocio

El container pattern mostrado aquí se integra perfectamente con los servicios AWS, permitiendo una gestión eficiente de recursos y una clara separación de responsabilidades. Esto es especialmente útil cuando necesitamos coordinar múltiples servicios AWS en una sola operación.

#### Configuración en `tests/aws.py`:

```python
import json
import os
from moto import mock_aws

with mock_aws():
    import boto3
    
    # SecretsManager
    secret = {f"{os.environ['PROJECT']}": {"key": "value"}}
    secrets = boto3.client("secretsmanager", region_name="us-east-2")
    secrets.create_secret(
        Name=f"database-global-secret-{os.environ['ENV']}", 
        SecretString=json.dumps(secret)
    )
    
    # SQS
    sqs = boto3.client("sqs", region_name="us-east-2")
    sqs.create_queue(
        QueueName="test-queue.fifo",
        Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
    )
    url = sqs.get_queue_url(QueueName="test-queue.fifo")["QueueUrl"]
    os.environ["QUEUE_URL"] = url
```

#### En tests específicos:

```python
@mock_aws  # SIEMPRE usar este decorador
def test_aws_service():
    import boto3
    
    # Los mocks ya están configurados por tests/aws.py
    client = boto3.client("secretsmanager", region_name="us-east-2")
    response = client.get_secret_value(SecretId="test-secret")
    assert response["SecretString"]
```

### Mocks de servicios:

```python
@pytest.fixture
def mock_boto3_client(mocker):
    """Mock genérico de cliente boto3"""
    mock_client = mocker.MagicMock()
    mocker.patch("boto3.client", return_value=mock_client)
    return mock_client
```


## 6. Testing en Frontend

### 6.1 Tipos de Testing

#### Unit Testing
- Utilizar Jest + React Testing Library (RTL) para tests unitarios de componentes
- Implementar mocking de dependencias para aislar componentes
- Cubrir casos borde y escenarios de error
- Co-localizar los tests junto a los componentes que prueban

#### Integration Testing
- Probar interacciones entre múltiples componentes
- Utilizar Mock Service Worker (msw) para simular llamadas API
- Validar flujos de datos entre componentes
- Probar hooks personalizados y lógica de negocio compartida

#### End-to-end (E2E) Testing
- Implementar tests E2E usando Playwright
- Cubrir flujos críticos de la aplicación
- Probar en múltiples navegadores y dispositivos
- Validar interacción entre componentes
- Verificar integración con APIs
- Comprobar manejo de errores de red
- Validar estados de carga
- Probar casos límite de integración
- Validar la experiencia del usuario completa

### 6.2 Organización y Estructura

#### Estructura de Directorios para Tests Frontend
```
src/
├── components/
│   ├── Button/
│   │   ├── Button.tsx
│   │   ├── Button.test.tsx
│   │   └── Button.stories.tsx
│   └── ...
├── hooks/
│   ├── useAuth/
│   │   ├── useAuth.ts
│   │   └── useAuth.test.ts
│   └── ...
└── __tests__/
    ├── integration/
    └── e2e/
```

#### Nomenclatura y Convenciones
- Archivos de test: `ComponentName.test.tsx` o `ComponentName.spec.tsx`
- Tests por funcionalidad o feature
- Nombres descriptivos que indiquen el comportamiento esperado
- Mantener consistencia en la estructura de los tests

### 6.3 Mejores Prácticas

#### Mocking y Stubbing
- Mockear dependencias externas y servicios
- Utilizar MSW para interceptar y simular llamadas API
- Crear stubs realistas que representen datos de producción
- Mantener los mocks centralizados y reutilizables

#### Aserciones y Validaciones
- Usar queries accesibles de RTL (getByRole, getByLabelText, etc.)
- Evitar selectores basados en implementación (querySelector, getByTestId)
- Validar comportamiento en lugar de implementación
- Incluir pruebas de accesibilidad

### Performance en Tests**:
- Agrupar tests similares para reducir setup
- Usar `beforeAll` para configuración costosa
- Implementar cleanup efectivo
- Evitar tests innecesariamente lentos
- Usar mocks para operaciones costosas
- Implementar test sharding en CI
- Mantener tests DRY usando helpers y fixtures
 - Documentar casos complejos o no obvios
- Mantener tests actualizados con el código
- Refactorizar tests cuando sea necesario

#### Consideraciones Especiales a tener en cuenta
- Probar manejo de errores y casos borde
- Validar responsividad y compatibilidad cross-browser
- Verificar el manejo de estructuras de datos complejas
- Asegurar la seguridad en el cliente (no exponer tokens/keys)
- **IMPORTANTE** Priorizar código crítico para el negocio

Este documento debe ser seguido estrictamente por todos los desarrolladores y copilotos IA para garantizar la consistencia y calidad de los tests en el proyecto.