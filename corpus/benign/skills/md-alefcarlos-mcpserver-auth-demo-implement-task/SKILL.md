---
name: implement-task
description: Implementa tasks do backlog.md que estão no status Refined. Revisa descrição, move para In Progress, implementa e marca como Done
license: MIT
compatibility: opencode
metadata:
  audience: developers
  workflow: backlog-implementation
---

## Quando usar
Quando o usuário pedir para implementar uma task que já está refinada (status "Refined").

## Pré-requisitos
- Task deve estar no status "Refined"
- Ter descrição clara com passos e pseudocódigo

## Como funciona
1. Peça o ID da task (ex: TASK-4)
2. Use `backlog_task_view` para buscar a task
3. Revise a descrição e confirme o entendimento com o usuário
4. Use `backlog_task_edit` para mudar status para "In Progress"
5. Siga os passos da descrição para implementar
6. Execute build e testes
7. Use o a ferramenta `review` para fazer code review automático:
   - Execute `/review` para analisar as mudanças
   - Apresente o resultado para o usuário confirmar
8. Após aprovação do review, use `backlog_task_edit` para mudar status para "Done"

## Padrão de status
- "Refined" → pronto para implementar
- "In Progress" → em implementação
- "Done" → implementado e testado
