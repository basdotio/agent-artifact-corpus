---
name: Carregar e Sanitizar Dados
description: Ler arquivos CSV ou Excel e aplicar tratamentos básicos de limpeza e padronização.
---

# Instruções da Skill

Esta skill fornece uma função utilitária para carregar e higienizar dados de planilhas e arquivos CSV de forma resiliente, seguindo o Protocolo Mestre do projeto.

## Script Disponível

O script `scripts/carregar_e_sanitizar.py` contém a função `skill_carregar_e_sanitizar(caminho: str) -> Dict[str, Any]`.

### Funcionalidades da Função:
- Identificação automática do formato (.csv, .xlsx, .xls)
- Leitura resiliente usando `engine='python'` para CSVs e `engine='openpyxl'` para Excel, lidando com problemas de encoding.
- **Divisão automática de colunas:** Se um cabeçalho contiver `:`, a coluna é dividida em duas (nome e conteúdo), mantendo a ordem.
- Remoção de linhas 100% vazias.
- Limpeza de colunas "fantasmas" (que começam com `Unnamed`).
- Padronização de cabeçalhos para o formato `snake_case` (minúsculas e sublinhados no lugar de espaços e pontos).

### Como o Agente DEVE usar

Sempre que a tarefa do usuário envolver carregamento inicial de planilhas ou CSVs que precisem de padronização estrutural na fase de preparação, importe e utilize o código dessa função. A função retorna um dicionário contendo o sumário (`sucesso`) ou os detalhes do erro (`erro`) para auxiliar na tomada de decisão do próprio agente ou para exibir relatórios prévios.

**Exemplo de integração no código:**
```python
from pathlib import Path
from typing import Dict, Any
# O agente pode copiar a definição da função ou importá-la do script da skill
# from scripts.carregar_e_sanitizar import skill_carregar_e_sanitizar

resultado = skill_carregar_e_sanitizar("caminho/do/arquivo.xlsx")

if resultado["status"] == "sucesso":
    print(f"Sucesso! {resultado['total_linhas']} linhas processadas.")
else:
    print(f"Erro: {resultado['mensagem']}")
```
