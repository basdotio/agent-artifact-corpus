---
name: lint
description: Python Linter (user)
license: MIT
---

# Python Linter

Executa análise de qualidade de código Python usando ferramentas de linting e formatação.

## Propósito

Esta skill automatiza a verificação de qualidade do código Python executando múltiplas ferramentas:
- **black** - Formatação de código
- **flake8** - Style guide enforcement (PEP 8)
- **isort** - Ordenação de imports
- **pylint** - Linting abrangente
- **mypy** - Type checking (opcional)

## Como Usar

### Modo Rápido (Recomendado)
```
/lint
```
Executa verificação completa com todas as ferramentas disponíveis.

### Modo Check-Only (Sem modificar arquivos)
```
/lint --check
```
Apenas reporta problemas, não aplica correções.

### Modo Fix (Auto-correção)
```
/lint --fix
```
Aplica correções automáticas sempre que possível.

### Escopo Específico
```
/lint --path src/
```
Executa linting apenas no diretório especificado.

## Fluxo de Execução

A skill segue esta ordem de execução:

```
┌─────────────────────────────────────────────────┐
│              PIPELINE DE LINTING                │
│                                                 │
│  1. black --check    (formatação)              │
│        ↓                                        │
│  2. isort --check    (imports)                 │
│        ↓                                        │
│  3. flake8           (style guide)             │
│        ↓                                        │
│  4. pylint           (linting completo)        │
│        ↓                                        │
│  5. [OPCIONAL] mypy  (type checking)           │
│                                                 │
│  Resultado: Resumo de todos os problemas       │
└─────────────────────────────────────────────────┘
```

## Ferramentas

### 1. Black (Formatação)

**O que verifica:**
- Line length (88 caracteres por padrão)
- Indentação consistente
- Quotes uniformes
- Trailing commas

**Comandos executados:**
```bash
# Check mode (padrão)
black --check .

# Fix mode
black .

# Arquivo específico
black src/main.py
```

**Configuração recomendada (pyproject.toml):**
```toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''
```

### 2. isort (Import Sorting)

**O que verifica:**
- Ordem de imports (stdlib → third-party → local)
- Agrupamento correto
- Linha em branco entre grupos

**Comandos executados:**
```bash
# Check mode
isort --check-only --diff .

# Fix mode
isort .
```

**Configuração recomendada (pyproject.toml):**
```toml
[tool.isort]
profile = "black"
line_length = 88
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
```

### 3. flake8 (Style Guide)

**O que verifica:**
- PEP 8 compliance
- McCabe complexity
- Naming conventions
- Unused imports/variables

**Comandos executados:**
```bash
flake8 . --max-line-length=88 --extend-ignore=E203,W503
```

**Configuração recomendada (.flake8):**
```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503, E501
exclude =
    .git,
    __pycache__,
    .venv,
    venv,
    build,
    dist,
    *.egg-info
max-complexity = 10
per-file-ignores =
    __init__.py: F401
    tests/*: F811
```

### 4. pylint (Comprehensive Linting)

**O que verifica:**
- Code smells
- Refactoring opportunities
- Convention violations
- Potential bugs

**Comandos executados:**
```bash
pylint src/ --fail-under=8.0
```

**Configuração recomendada (.pylintrc):**
```ini
[MASTER]
ignore=CVS,.git,__pycache__,.venv

[MESSAGES CONTROL]
disable=
    C0111,  # missing-docstring
    R0903,  # too-few-public-methods
    C0103,  # invalid-name

[FORMAT]
max-line-length=88

[DESIGN]
max-args=7
max-attributes=10
max-branches=15
```

### 5. mypy (Type Checking - Opcional)

**O que verifica:**
- Type annotations corretas
- Type compatibility
- Missing type hints

**Comandos executados:**
```bash
mypy . --ignore-missing-imports
```

**Configuração recomendada (pyproject.toml):**
```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
exclude = [
    'venv',
    '.venv',
    'tests'
]
```

## Interpretação de Resultados

### ✅ Sucesso (Score 10/10)
```
✅ black: All files formatted correctly
✅ isort: All imports sorted correctly
✅ flake8: No style violations found
✅ pylint: Score 10.0/10
```

### ⚠️ Warnings (Score 7-9/10)
```
⚠️ black: 3 files would be reformatted
⚠️ isort: 2 files would be reordered
✅ flake8: No violations
⚠️ pylint: Score 8.5/10
   - src/main.py:45: C0301 (line-too-long)
   - src/utils.py:12: W0612 (unused-variable)
```

### ❌ Errors (Score <7/10)
```
❌ black: 15 files would be reformatted
❌ isort: 8 files would be reordered
❌ flake8: 23 violations found
   - E501: line too long (92 > 88 characters) × 12
   - F401: imported but unused × 7
   - W503: line break before binary operator × 4
❌ pylint: Score 6.2/10
   - Multiple convention violations
   - Code complexity issues
```

## Auto-Fix Strategy

Quando executado com `--fix`, a skill:

1. **black** (auto-fix 100%)
   - Reformata todos os arquivos automaticamente

2. **isort** (auto-fix 100%)
   - Reordena imports automaticamente

3. **flake8** (auto-fix 50%)
   - Remove unused imports
   - Fix trailing whitespace
   - Alguns erros requerem correção manual

4. **pylint** (auto-fix 20%)
   - Maioria requer intervenção manual
   - Skill sugere correções específicas

## Instalação de Dependências

Se as ferramentas não estiverem instaladas:

```bash
# Instalar todas as ferramentas
pip install black flake8 isort pylint mypy

# Ou via requirements-dev.txt
pip install -r requirements-dev.txt
```

**requirements-dev.txt:**
```
black==24.1.0
flake8==7.0.0
isort==5.13.2
pylint==3.0.3
mypy==1.8.0
flake8-docstrings==1.7.0
flake8-bugbear==24.1.0
```

## Integração com CI/CD

### GitHub Actions
```yaml
name: Lint
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install black flake8 isort pylint
      - name: Run linters
        run: |
          black --check .
          isort --check-only .
          flake8 .
          pylint src/ --fail-under=8.0
```

### Pre-commit Hook
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
```

## Boas Práticas

1. **Execute antes de commit**
   ```bash
   /lint --fix
   git add .
   git commit -m "fix: apply linting fixes"
   ```

2. **Configure uma vez, use sempre**
   - Crie arquivos de configuração no projeto
   - Commite as configurações (.flake8, pyproject.toml, .pylintrc)

3. **Use em CI/CD**
   - Bloqueia PRs com code quality ruim
   - Mantém padrão consistente no time

4. **Progressive Enhancement**
   - Comece com black + isort (fácil)
   - Adicione flake8 (médio)
   - Gradualmente melhore score do pylint (difícil)

5. **Ignore false positives**
   - Use `# noqa` para suprimir warnings específicos
   - Configure exclusões por arquivo em .flake8

## Troubleshooting

### Black vs Flake8 conflitos
**Problema:** flake8 reclama de formatação que black considera correta

**Solução:** Configure flake8 para ser compatível com black:
```ini
[flake8]
extend-ignore = E203, W503
max-line-length = 88
```

### isort vs Black conflitos
**Problema:** isort e black formatam imports diferente

**Solução:** Configure isort com profile black:
```toml
[tool.isort]
profile = "black"
```

### Pylint score muito baixo
**Problema:** Score 3.5/10 em projeto legado

**Solução:** Progressive improvement:
1. Desabilite algumas regras inicialmente
2. Foque em bugs reais (E, F)
3. Depois convenções (C, R, W)

### Mypy demais erros
**Problema:** 500+ type errors em projeto sem type hints

**Solução:**
```ini
[tool.mypy]
ignore_missing_imports = true
disallow_untyped_defs = false  # Gradualmente ative
```

## Exemplo de Saída Completa

```
🔍 Python Linting - Análise de Qualidade de Código

📂 Escopo: . (current directory)
🔧 Modo: check (read-only)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1️⃣ BLACK (Code Formatting)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ All 47 files formatted correctly

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2️⃣ ISORT (Import Sorting)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  2 files need import reordering:
    - src/main.py
    - src/utils/helpers.py

Run with --fix to auto-correct

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3️⃣ FLAKE8 (Style Guide)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ 5 violations found:

src/main.py:45:10: E501 line too long (92 > 88)
src/main.py:78:1: F401 'os' imported but unused
src/utils/helpers.py:12:5: W0612 unused variable 'result'
src/config.py:23:80: E231 missing whitespace after ','
tests/test_main.py:5:1: F811 redefinition of unused 'mock'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4️⃣ PYLINT (Comprehensive Linting)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Your code has been rated at 8.75/10

src/main.py:45: C0301 (line-too-long)
src/utils/helpers.py:12: W0612 (unused-variable)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 RESUMO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ black:  PASS
⚠️  isort:  2 fixes needed
❌ flake8: 5 violations
⚠️  pylint: 8.75/10

🎯 Score Geral: 8.2/10

💡 Próximos passos:
1. Execute: /lint --fix (corrige black + isort automaticamente)
2. Corrija manualmente os 5 erros do flake8
3. Re-execute para validar

🚀 Para aplicar correções automáticas: /lint --fix
```

## Referências

- [Black Documentation](https://black.readthedocs.io/)
- [flake8 Documentation](https://flake8.pycqa.org/)
- [isort Documentation](https://pycqa.github.io/isort/)
- [Pylint Documentation](https://pylint.pycqa.org/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [PEP 8 Style Guide](https://pep8.org/)
