# Python Code Guidelines

Esta guia define el estandar para escribir y mantener código Python dentro de repositorios de
desarrollo de software de HABI.

---

## Verificación del submódulo .code_quality

### Verificación obligatoria

Antes de comenzar el desarrollo en cualquier proyecto Python de HABI, verificar si existe el
submódulo `.code_quality` ya que este es indispensable para pasar las reglas de sonarQube:

```bash
# Verificar si existe el submódulo
ls -la .code_quality/

# Si no existe, verificar si está configurado como submódulo
git submodule status | grep .code_quality

# Si no está configurado, agregarlo como submódulo
git submodule add https://gitlab.com/habi_co/transversal/backend-linter.git .code_quality

# Si ya está configurado pero no descargado, inicializarlo y descargarlo
git submodule update --init --recursive .code_quality

# Para proyectos existentes que ya tienen el submódulo configurado
git submodule update --init --recursive
```

---

## Configuración de dependencias

**OBLIGATORIO**: El submódulo `.code_quality` ya incluye todas las dependencias y configuraciones
necesarias. No se requieren configuraciones manuales adicionales.

## Herramientas de validación y formateo

**OBLIGATORIO**: Todos los proyectos Python de HABI DEBEN contener el submódulo `.code_quality` que
incluye todas las configuraciones y herramientas de validación. Este submódulo es indispensable para
pasar las reglas de SonarQube.

Para asegurar que las reglas de este documento se apliquen de forma consistente:

### Black (formateador de código)

- El submódulo `.code_quality` ya incluye la configuración de Black. Para formatear código:

```bash
black --line-length 120 .
```

### Pylint (linter)

- El submódulo `.code_quality` ya incluye la configuración de Pylint. Para ejecutar:

```bash
pylint --rcfile=.code_quality/.code_quality/.pylintrc --fail-under=10.0 src/ tests/
```

### Flake8 (linter adicional)

- El submódulo `.code_quality` ya incluye la configuración de Flake8. Para ejecutar:

```bash
flake8 --config=.code_quality/.code_quality/.flake8 src/ tests/
```

### isort (organizador de imports)

- El submódulo `.code_quality` ya incluye la configuración de isort. Para ordenar imports:

```bash
isort --profile black .
```

### Bandit (análisis de seguridad)

- El submódulo `.code_quality` ya incluye la configuración de Bandit. Para ejecutar:

```bash
bandit -r src/
```

### Mypy (verificador de tipos estático)

- El submódulo `.code_quality` ya incluye la configuración de Mypy. Para ejecutar:

```bash
mypy src/
```

---

## Estilo de código (PEP 8)

- Sigue estrictamente las convenciones de **PEP 8** para el estilo de código Python.
- Utiliza **4 espacios** para indentación, nunca tabs.
- Mantén un ancho máximo de línea de **120 caracteres** (Establecido por comite HABI).
- Usa **snake_case** para nombres de variables y funciones.
- Usa **PascalCase** para nombres de clases.
- Usa **UPPER_CASE** para constantes.
- **IMPORTANTE**: Todos los comentarios, docstrings, nombres de funciones y variables deben
  escribirse en **INGLÉS**.

Ejemplo:

```python
def calculate_average(numbers):
    """Calculates the average of a list of numbers."""
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)

class StatisticalCalculator:
    """Class for performing basic statistical calculations."""

    PI_CONSTANT = 3.14159

    def __init__(self):
        self.history = []
```

---

## Reglas de Pylint

### Configuración general

- Establece un puntaje mínimo de **10.0/10** para pasar las validaciones.
- **Las reglas de estilo y formato NUNCA se pueden deshabilitar** para mantener la calidad del
  código.
- **Las reglas opcionales se pueden deshabilitar** según la configuración del submódulo
  `.code_quality` mantenido por devops.

### Reglas OBLIGATORIAS (nunca deshabilitar - Estilo y Formato)

**Estas reglas son CRÍTICAS para mantener la calidad del código y NUNCA se pueden deshabilitar:**

- **C0114** - Missing module docstring
- **C0115** - Missing class docstring
- **C0116** - Missing function or method docstring
- **C0103** - Invalid name (nombres de variables/funciones)
- **C0301** - Line too long
- **C0326** - Bad whitespace
- **C0302** - Too many lines in module
- **C0303** - Trailing whitespace
- **C0321** - Multiple statements on one line
- **C0111** - Unused import
- **C0112** - Empty docstring
- **C0113** - Unneeded not

### Reglas OPCIONALES (se pueden deshabilitar según .code_quality)

**Estas reglas se pueden deshabilitar según la configuración del submódulo .code_quality para**
**mantener compatibilidad y flexibilidad en el desarrollo:**

#### **Compatibilidad Python 2/3:**

- `basestring-builtin`, `buffer-builtin`, `cmp-builtin`, `execfile-builtin`
- `file-builtin`, `input-builtin`, `intern-builtin`, `long-builtin`
- `raw_input-builtin`, `reload-builtin`, `unicode-builtin`, `xrange-builtin`

#### **Métodos especiales y builtins:**

- `apply-builtin`, `coerce-builtin`, `reduce-builtin`, `round-builtin`
- `delslice-method`, `div-method`, `getslice-method`, `setslice-method`
- `hex-method`, `idiv-method`, `next-method`, `nonzero-method`, `oct-method`

#### **Imports y módulos:**

- `import-error`, `import-self`, `import-star-module-level`
- `no-absolute-import`, `no-name-in-module`, `relative-import`
- `wrong-import-order`

#### **Otros:**

- `abstract-method`, `arguments-differ`, `attribute-defined-outside-init`
- `no-init`, `no-member`, `no-self-use`, `too-few-public-methods`
- `duplicate-code`, `c-extension-no-member`, `fixme`, `global-statement`

### Configuración de Pylint

**Nota**: El submódulo `.code_quality` ya incluye la configuración completa de Pylint. Este ejemplo
es solo de referencia para entender la configuración:

```ini
[MASTER]
# Solo deshabilitar reglas según el submódulo .code_quality
# Las reglas de estilo y formato NUNCA se pueden deshabilitar

[FORMAT]
max-line-length=120
good-names=i,j,k,ex,Run,_,id

[MESSAGES CONTROL]
# Solo deshabilitar reglas opcionales según .code_quality
# disable=R,abstract-method,arguments-differ,no-member,etc.

[REPORTS]
output-format=text
score=yes
min-similarity-lines=4
```

---

## Reglas de Flake8

### Configuración general

- Establece un límite de línea de **120 caracteres**.
- Ignora solo los códigos de error que sean absolutamente necesarios.

### Reglas críticas (nunca ignorar)

- **E1** - Indentation errors
- **E2** - Whitespace errors
- **E3** - Blank line errors
- **E4** - Import errors
- **E5** - Line length errors
- **E9** - Runtime errors

### Reglas recomendadas

- **F401** - Unused imports
- **F403** - Wildcard imports
- **F405** - Name may be undefined
- **F811** - Redefinition while unused
- **F812** - List comprehension redefines name
- **F821** - Undefined name
- **F822** - Undefined name in **all**
- **F823** - Local variable referenced before assignment
- **F831** - Duplicate argument name
- **F841** - Local variable assigned but never used

### Configuración de Flake8

**Nota**: El submódulo `.code_quality` ya incluye la configuración completa de Flake8. Este ejemplo
es solo de referencia para entender la configuración:

```ini
[flake8]
max-line-length = 120
extend-ignore =
    E203,  # Whitespace before ':'
    W503,  # Line break before binary operator
    E501,  # Line too long (manejado por Black)
exclude =
    .git,
    __pycache__,
    .venv,
    venv,
    .env,
    build,
    dist
per-file-ignores =
    __init__.py:F401
    tests/*:F401,F403
```

---

## Reglas de Bandit

### Configuración general

- **OBLIGATORIO**: Bandit es una herramienta de análisis de seguridad estática para Python.
- Se ejecuta como parte del pipeline de CI/CD para detectar vulnerabilidades de seguridad.
- El submódulo `.code_quality` ya incluye la configuración de Bandit.

### Reglas críticas de seguridad (nunca ignorar)

- **B101** - Use of assert detected
- **B102** - Use of exec detected
- **B103** - Set a random seed
- **B104** - Hardcoded bind address
- **B105** - Hardcoded password string
- **B201** - Flask debug mode
- **B301** - Pickle and modules that wrap it
- **B302** - marshal
- **B303** - md5
- **B307** - eval
- **B310** - urllib_urlopen
- **B311** - random
- **B312** - telnetlib
- **B321** - ftplib
- **B322** - input
- **B401** - import_telnetlib
- **B402** - import_ftplib
- **B403** - import_pickle
- **B404** - import_subprocess
- **B501** - request_with_no_cert_validation
- **B601** - paramiko_calls
- **B602** - subprocess_popen_with_shell_equals_true
- **B608** - hardcoded_sql_expressions
- **B701** - jinja2_autoescape_false

### Configuración de Bandit

**Nota**: El submódulo `.code_quality` ya incluye la configuración completa de Bandit. Este ejemplo
es solo de referencia para entender la configuración:

```ini
[bandit]
exclude_dirs = tests,venv,.venv,.git
skips = B101,B601
targets = src/
```

---

## Reglas de Mypy

### Configuración general

- **OBLIGATORIO**: Mypy es un verificador de tipos estático para Python.
- Se ejecuta como parte del pipeline de CI/CD para validar anotaciones de tipos.
- El submódulo `.code_quality` ya incluye la configuración de Mypy.

### Reglas críticas de tipos (nunca ignorar)

- **E1** - Syntax errors
- **E2** - Name errors
- **E3** - Type errors
- **E4** - Import errors
- **E5** - Attribute errors
- **E6** - Expression errors
- **E7** - Statement errors
- **E8** - Semantic errors
- **E9** - Runtime errors

### Configuración de Mypy

**Nota**: El submódulo `.code_quality` ya incluye la configuración completa de Mypy. Este ejemplo es
solo de referencia para entender la configuración:

```ini
[mypy]
python_version = 3.8
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True
```

---

## Documentación y docstrings

### Formato de docstrings

- Usa **Google Style** para docstrings (compatible con Sphinx).
- Incluye docstrings en todos los módulos, clases y funciones públicas.
- Para funciones privadas, usa docstrings simples o comentarios.
- **OBLIGATORIO**: Todos los docstrings deben escribirse en **INGLÉS**.

Ejemplo:

```python
def process_data(input_data, configuration=None):
    """Processes input data according to the specified configuration.

    Args:
        input_data (list): List of data to process.
        configuration (dict, optional): Processing configuration.
            Defaults to None.

    Returns:
        dict: Processing result with statistics.

    Raises:
        ValueError: If input data is empty.
        TypeError: If data type is not compatible.

    Example:
        >>> data = [1, 2, 3, 4, 5]
        >>> result = process_data(data)
        >>> print(result['average'])
        3.0
    """
    if not input_data:
        raise ValueError("Input data cannot be empty")

    # ... rest of the code
```

---

## Imports y organización

### Orden de imports

- Usa **isort** para ordenar automáticamente los imports.
- Agrupa los imports en el siguiente orden:
  1. Imports de la biblioteca estándar
  2. Imports de terceros
  3. Imports locales del proyecto
- **IMPORTANTE**: Todos los nombres de módulos, paquetes y archivos deben estar en **INGLÉS**.

### Configuración de isort

```ini
[isort]
profile = black
line_length = 120
multi_line_output = 3
include_trailing_comma = True
force_grid_wrap = 0
use_parentheses = True
ensure_newline_before_comments = True
```

### Ejemplo de imports organizados

```python
# Standard library imports
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Third-party imports
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException

# Local imports
from .models import DataModel
from .utils import process_data
```

---

## Manejo de errores y excepciones

### Reglas generales

- Usa excepciones específicas en lugar de `Exception` genérica.
- Incluye mensajes de error descriptivos y útiles en **INGLÉS**.
- Usa `logging` para registrar errores y eventos importantes.
- Implementa manejo de errores apropiado en funciones públicas.

### Ejemplo de manejo de errores

```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def divide_numbers(dividend: float, divisor: float) -> Optional[float]:
    """Divides two numbers with appropriate error handling."""
    try:
        if divisor == 0:
            raise ValueError("Divisor cannot be zero")

        result = dividend / divisor
        logger.info(f"Successful division: {dividend} / {divisor} = {result}")
        return result

    except ValueError as e:
        logger.error(f"Value error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during division: {e}")
        raise RuntimeError(f"Error processing division: {e}")
```

---

## Testing y cobertura

**IMPORTANTE**: Ver la estrategia de testing y cobertura en el documento/regla testing.md

## Pre-commit hooks

**Configuración obligatoria**: Todos los proyectos deben configurar pre-commit hooks para ejecutar
todas las validaciones.

```bash
# Verificar si pre-commit ya está instalado
if command -v pre-commit &> /dev/null; then
    echo "✅ pre-commit ya está instalado"
    pre-commit --version
else
    echo "⚠️  pre-commit no está instalado. Instalando..."
    pip install pre-commit
fi

# Verificar que pre-commit esté funcionando
pre-commit --version

# Configurar pre-commit usando el submódulo .code_quality
pre-commit install -c .code_quality/.pre-commit-config.yaml


```

**IMPORTANTE**: El submódulo `.code_quality` es OBLIGATORIO para todos los proyectos Python de HABI.
Todas las configuraciones y herramientas ya están configuradas en el submódulo. Solo es necesario
activarlas y verificar que Pylint esté configurado para puntaje 10.0/10 y que las reglas
obligatorias de estilo y formato NUNCA estén deshabilitadas.
