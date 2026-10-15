
# Filosofía General

El código se lee más de lo que se escribe: Priorizamos la claridad y la legibilidad sobre la concisión excesiva.

La calidad es responsabilidad de todos: Las herramientas automatizadas son una ayuda, no un sustituto del buen juicio del desarrollador.

Consistencia ante todo: Un estilo de código uniforme en todo el proyecto facilita la comprensión y reduce la carga cognitiva.

## Estilo y Formateo de Código

Nuestro estándar se basa en PEP 8, con algunas reglas específicas y reforzadas.

Límite de Longitud de Línea: Todas las líneas de código deben tener un máximo de 80 caracteres. Esto mejora la legibilidad, especialmente en pantallas divididas.

Convención de Nomenclatura: Se debe usar snake_case para todas las variables y nombres de funciones (ej: calcular_total_factura).

## Calidad y Robustez del Código

Más allá del estilo, el código debe ser robusto, mantenible y predecible.

Complejidad Ciclomática: Las funciones y métodos no deben exceder una complejidad ciclomática de 15. Si una función es más compleja, es una señal de que debe ser refactorizada en unidades más pequeñas y manejables. pylint y flake8 (con plugins) medirán esto.

Manejo de Excepciones: Está prohibido usar excepciones genéricas como except Exception: o except:. Siempre se deben capturar las excepciones más específicas posibles (ej: except ValueError:, except FileNotFoundError:). Esto evita ocultar errores inesperados y hace que el flujo de control sea más explícito.

## Herramientas de Calidad de Código

Nuestro flujo de trabajo automatizado se apoya en las siguientes herramientas:

flake8: Un linter rápido y eficiente que verifica el cumplimiento de PEP 8, errores de sintaxis y la complejidad del código.

pylint: Proporciona un análisis más profundo del código, detectando "code smells", reforzando estándares de codificación y buscando errores lógicos.

bandit: Una herramienta de análisis estático de seguridad (SAST) que escanea el código en busca de vulnerabilidades de seguridad comunes en Python.

sqlfluff: Un linter de SQL que garantiza la consistencia y legibilidad de las consultas.

Uso en Python: Dado que nuestro código SQL a menudo se encuentra dentro de variables de cadena (strings) en Python, sqlfluff se configurará para analizar estas cadenas, asegurando que incluso el SQL embebido cumpla con nuestros estándares de calidad

## Principios de Diseño de Software: SOLID

Además de las reglas de estilo y calidad, nuestro equipo se adhiere a los principios de diseño SOLID para crear un software robusto y fácil de mantener.
