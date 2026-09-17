# Skill: ServiceNow SPM Quality TM2 (Test Management)

Este skill capacita o agente a avaliar a qualidade e a confiabilidade das entregas no ServiceNow, integrando o desenvolvimento ágil com o Test Management 2.0 (TM2).

## Tabelas de Referência (Escopo Qualidade/TM2)

- **`sn_test_management_test`**: Casos de teste manuais/automatizados.
- **`sn_test_management_test_result`**: Resultados das execuções.
- **`sn_test_management_test_plan`**: Planos de teste estruturados.
- **`sn_st_mgmt_test`**: Testes de serviço e monitoramento (Zurich).

## Fluxo de Qualidade

1. **Associação**: Uma `rm_story` ou `pm_project_task` deve ter testes vinculados.
2. **Execução**: O teste é executado e o resultado é registrado na `test_result`.
3. **Validação**: O agente verifica se o resultado foi `Passed` antes de considerar a evolução saudável.

## Indicadores de Saúde (Quality TM2)

| Indicador | Dimensão | Tabela/Campo | Descrição |
|-----------|----------|--------------|-----------|
| **Pass Rate** | Qualidade | `sn_test_management_test_result` | % de testes com sucesso em relação ao total executado. |
| **Test Coverage** | Abrangência | `m2m_task_test` | Volume de tarefas com pelo menos um teste vinculado. |
| **Regression Failure** | Estabilidade | `sn_test_management_test_result` | Falhas em testes marcados como regressão. |
| **Environment Readiness** | Risco | `test_environment` | Disponibilidade e status dos ambientes de teste. |

## Ferramentas MCP Recomendadas

- `sn_table_query`: Para cruzar resultados de testes com tarefas específicas.
- `ph_project_task_list_v1`: Para identificar tarefas que requerem validação de teste.

## Exemplo de Query (Grep/Pattern)

Para listar falhas de teste no último ciclo:
`sysparm_query=status=failed^sys_created_onONToday@javascript:gs.daysAgoStart(0)@javascript:gs.daysAgoEnd(0)`
